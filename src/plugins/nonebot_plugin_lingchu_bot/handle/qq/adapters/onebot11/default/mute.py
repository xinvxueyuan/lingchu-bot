import json
from dataclasses import dataclass
from typing import Any

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

from ......core.runtime_config import get_handle_config_manager, runtime_config
from ......i18n import _async as _
from ......permissions.subject_policy import find_active_subject_policy
from ......repositories import message_store as message_repository
from ....commands.common import selected_adapter_handle
from ....commands.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    recall_message_cmd,
    whole_mute_cmd,
    whole_unmute_cmd,
)
from .common import (
    MUTE_DURATION_MAX,
    MUTE_DURATION_MIN,
    CommandAudit,
    bot_id,
    bot_self_id_safe,
    check_bot_privilege,
    check_self_target,
    check_target_privilege,
    format_user_display_name,
    record_audit_fire_and_forget,
    resolve_user_onebot11,
)

RECALL_COUNT_MAX = 100


def _message_id_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sender_id_from_message(value: dict[str, Any]) -> int | None:
    sender = value.get("sender")
    if not isinstance(sender, dict):
        return None
    return _message_id_int(sender.get("user_id"))


def _group_id_matches(value: dict[str, Any], group_id: int) -> bool:
    actual = value.get("group_id")
    if actual is None:
        return True
    return _message_id_int(actual) == group_id


def _message_type_matches(value: dict[str, Any]) -> bool:
    message_type = value.get("message_type")
    return message_type is None or message_type == "group"


async def _verified_recall_message(
    bot: OneBot11Bot,
    *,
    message_id: int,
    group_id: int,
    target_user_id: int | None,
) -> dict[str, Any] | None:
    try:
        message = await bot.get_msg(message_id=message_id)
    except OneBot11ActionFailed:
        logger.debug(f"撤回校验失败，消息不存在或不可访问: message_id={message_id}")
        return None
    if not isinstance(message, dict):
        return None
    if not _message_type_matches(message) or not _group_id_matches(message, group_id):
        return None
    sender_id = _sender_id_from_message(message)
    if target_user_id is not None and sender_id != target_user_id:
        return None
    return message


async def _is_recall_protected_target(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    target_user_id: int,
) -> bool:
    if "recall_message" not in runtime_config.protected_subject_feature_keys:
        return False
    protected = await find_active_subject_policy(
        policy_type="protected",
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id=bot_id(bot),
        group_id=event.group_id,
        user_id=target_user_id,
    )
    return protected is not None


async def _can_recall_sender(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    sender_id: int,
) -> bool:
    if sender_id == event.user_id:
        return False
    bot_self = bot_self_id_safe(bot)
    if bot_self is not None and sender_id == bot_self:
        return False
    if await _is_recall_protected_target(bot, event, sender_id):
        return False
    try:
        member_info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=sender_id,
            no_cache=True,
        )
    except OneBot11ActionFailed:
        return True
    return member_info.get("role", "member") not in ("admin", "owner")


def _candidate_fetch_limit(count: int) -> int:
    return min(max(count * 5, count + 20), 500)


def _record_conversation_id(record: Any) -> str | None:
    value = getattr(record, "conversation_id", None)
    return value if isinstance(value, str) else None


def _record_raw_event(record: Any) -> dict[str, Any] | None:
    raw_event = getattr(record, "raw_event", None)
    if not isinstance(raw_event, str):
        return None
    try:
        parsed = json.loads(raw_event)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _record_belongs_to_group(record: Any, group_id: int) -> bool:
    group_id_text = str(group_id)
    conversation_id = _record_conversation_id(record)
    if conversation_id == group_id_text:
        return True
    if conversation_id is not None and conversation_id.startswith(
        f"group_{group_id_text}_"
    ):
        return True
    raw_event = _record_raw_event(record)
    if raw_event is None:
        return False
    return _message_id_int(raw_event.get("group_id")) == group_id


def _merge_recall_candidates(
    *record_groups: list[Any],
    group_id: int,
) -> list[Any]:
    records: list[Any] = []
    seen: set[str] = set()
    for group in record_groups:
        for record in group:
            message_id = getattr(record, "message_id", None)
            key = str(message_id) if message_id is not None else f"id:{id(record)}"
            if key in seen or not _record_belongs_to_group(record, group_id):
                continue
            seen.add(key)
            records.append(record)
    return records


async def _list_recall_candidate_records(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    *,
    target_user_id: int | None,
    recall_count: int,
) -> list[Any]:
    fetch_limit = _candidate_fetch_limit(recall_count)
    common_filters: dict[str, Any] = {
        "platform_id": "qq",
        "adapter_id": "~onebot.v11",
        "bot_id": bot_id(bot),
        "user_id": str(target_user_id) if target_user_id is not None else None,
    }
    broad_records = await message_repository.list_recent_messages(
        **common_filters,
        limit=min(fetch_limit * 2, 500),
    )
    group_records = await message_repository.list_recent_messages(
        **common_filters,
        conversation_id=str(event.group_id),
        limit=fetch_limit,
    )
    return _merge_recall_candidates(
        broad_records,
        group_records,
        group_id=event.group_id,
    )


async def _resolve_recall_args(
    target: At | int | None,
    count: int | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> tuple[int | None, str | None, int]:
    # 读取配置中的默认撤回数量
    config = await get_handle_config_manager().get_config("recall_message")
    default_count = config.defaults.get("default_count", 10)

    if isinstance(target, At):
        target_user_id, target_name = await resolve_user_onebot11(target, bot, event)
        return (
            target_user_id,
            target_name,
            count if count is not None else default_count,
        )
    if isinstance(target, int) and count is not None:
        target_user_id, target_name = await resolve_user_onebot11(target, bot, event)
        return target_user_id, target_name, count
    if isinstance(target, int):
        return None, None, target
    return None, None, count if count is not None else default_count


@dataclass(slots=True)
class RecallResult:
    recalled: int = 0
    skipped: int = 0
    failed: int = 0


async def _recall_record_message(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    record: Any,
    *,
    trigger_message_id: str,
    target_user_id: int | None,
) -> str:
    message_id = _message_id_int(getattr(record, "message_id", None))
    if message_id is None or str(message_id) == trigger_message_id:
        return "skipped"
    message = await _verified_recall_message(
        bot,
        message_id=message_id,
        group_id=event.group_id,
        target_user_id=target_user_id,
    )
    if message is None:
        return "skipped"
    sender_id = _sender_id_from_message(message)
    if sender_id is None:
        sender_id = _message_id_int(getattr(record, "user_id", None))
    if sender_id is None or not await _can_recall_sender(bot, event, sender_id):
        return "skipped"
    try:
        await bot.delete_msg(message_id=message_id)
    except OneBot11ActionFailed as e:
        logger.warning(f"撤回失败: message_id={message_id}, error={e!r}")
        return "failed"
    return "recalled"


async def _recall_records(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    records: list[Any],
    *,
    target_user_id: int | None,
    recall_count: int,
) -> RecallResult:
    result = RecallResult()
    trigger_message_id = str(getattr(event, "message_id", ""))
    for record in records:
        if result.recalled >= recall_count:
            break
        status = await _recall_record_message(
            bot,
            event,
            record,
            trigger_message_id=trigger_message_id,
            target_user_id=target_user_id,
        )
        if status == "recalled":
            result.recalled += 1
        elif status == "failed":
            result.failed += 1
        else:
            result.skipped += 1
    return result


@selected_adapter_handle(member_mute_cmd, "~onebot.v11", "member_mute")
async def onebot11_mute(
    user: At | int,
    duration: int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await member_mute_cmd.finish(await _("该功能已禁用"))

    # 读取配置参数
    default_mute_duration = config.defaults.get("mute_duration", 300)
    default_reason_text = config.defaults.get("default_reason", "管理员操作")

    # 如果用户没有提供duration，使用配置中的默认值
    actual_duration = duration if duration is not None else default_mute_duration

    # 1. 参数合法性检查
    if actual_duration < MUTE_DURATION_MIN:
        return await member_mute_cmd.finish(
            (await _("禁言时长不能小于 {min} 秒")).format(min=MUTE_DURATION_MIN)
        )
    if actual_duration > MUTE_DURATION_MAX:
        return await member_mute_cmd.finish(
            (await _("禁言时长不能超过 {max} 秒（30天）")).format(max=MUTE_DURATION_MAX)
        )

    # 2. 解析用户
    try:
        target_user_id, target_name = await resolve_user_onebot11(user, bot, event)
    except ValueError as e:
        logger.warning(f"解析用户失败: {e}")
        return await member_mute_cmd.finish(str(e))

    # 3. 边界条件检查
    if not await check_self_target(target_user_id, bot, event, member_mute_cmd, "禁言"):
        return None

    if not await check_target_privilege(bot, event, target_user_id, member_mute_cmd):
        return None

    # 4. 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, member_mute_cmd):
        return None

    # 5. 执行禁言操作
    try:
        await bot.set_group_ban(
            group_id=event.group_id, user_id=target_user_id, duration=actual_duration
        )
    except OneBot11ActionFailed as e:
        logger.error(f"禁言失败，操作被拒绝: {e!r}")
        return await member_mute_cmd.finish(await _("禁言失败，操作被拒绝"))

    # 6. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="member_mute",
            target_user_id=target_user_id,
            duration=actual_duration,
            reason=reason,
        ),
    )

    # 7. 格式化反馈消息
    reason_text = await _(default_reason_text) if reason is None else reason
    name_display = format_user_display_name(target_user_id, target_name)
    message = await _(
        "已禁言: \n"
        "名称: {name_display}\n"
        "时长: {duration} 秒\n"
        "原因: {reason}\n"
        "标识: {target_user_id}"
    )
    return await member_mute_cmd.finish(
        message.format(
            name_display=name_display,
            duration=actual_duration,
            reason=reason_text,
            target_user_id=target_user_id,
        )
    )


@selected_adapter_handle(whole_mute_cmd, "~onebot.v11", "whole_mute")
async def onebot11_whole_mute(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 检查功能是否启用（全体禁言共用member_mute配置）
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await whole_mute_cmd.finish(await _("该功能已禁用"))

    # 1. 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, whole_mute_cmd):
        return None

    # 2. 执行全体禁言操作
    try:
        await bot.set_group_whole_ban(group_id=event.group_id, enable=True)
    except OneBot11ActionFailed as e:
        logger.error(f"全体禁言失败，操作被拒绝: {e!r}")
        return await whole_mute_cmd.finish(await _("全体禁言失败，操作被拒绝"))

    # 3. 记录审计
    await record_audit_fire_and_forget(bot, event, CommandAudit(action="whole_mute"))

    return await whole_mute_cmd.finish(await _("全体禁言成功"))


@selected_adapter_handle(member_unmute_cmd, "~onebot.v11", "member_unmute")
async def onebot11_unmute(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 检查功能是否启用（解禁共用member_mute配置）
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await member_unmute_cmd.finish(await _("该功能已禁用"))

    # 1. 解析用户
    try:
        target_user_id, target_name = await resolve_user_onebot11(user, bot, event)
    except ValueError as e:
        logger.warning(f"解析用户失败: {e}")
        return await member_unmute_cmd.finish(str(e))

    # 2. 边界条件检查
    if target_user_id == event.user_id:
        return await member_unmute_cmd.finish(await _("不能解禁自己"))

    bot_self_id = bot_self_id_safe(bot)
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await member_unmute_cmd.finish(await _("不能解禁机器人"))

    # 3. 执行解禁操作
    try:
        await bot.set_group_ban(
            group_id=event.group_id, user_id=target_user_id, duration=0
        )
    except OneBot11ActionFailed as e:
        logger.error(f"解禁失败，操作被拒绝: {e!r}")
        return await member_unmute_cmd.finish(await _("解禁失败，操作被拒绝"))

    # 4. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(action="member_unmute", target_user_id=target_user_id),
    )

    # 5. 格式化反馈消息
    name_display = format_user_display_name(target_user_id, target_name)
    message = await _("已解禁: \n名称: {name_display}\n标识: {target_user_id}")
    return await member_unmute_cmd.finish(
        message.format(
            name_display=name_display,
            target_user_id=target_user_id,
        )
    )


@selected_adapter_handle(whole_unmute_cmd, "~onebot.v11", "whole_unmute")
async def onebot11_whole_unmute(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 检查功能是否启用（全体解禁共用member_mute配置）
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await whole_unmute_cmd.finish(await _("该功能已禁用"))

    try:
        await bot.set_group_whole_ban(group_id=event.group_id, enable=False)
    except OneBot11ActionFailed as e:
        logger.error(f"全体解禁失败，操作被拒绝: {e!r}")
        return await whole_unmute_cmd.finish(await _("全体解禁失败，操作被拒绝"))

    # 记录审计
    await record_audit_fire_and_forget(bot, event, CommandAudit(action="whole_unmute"))

    return await whole_unmute_cmd.finish(await _("全体解禁成功"))


@selected_adapter_handle(recall_message_cmd, "~onebot.v11", "recall_message")
async def onebot11_recall_message(
    target: At | int | None = None,
    count: int | None = None,
    bot: OneBot11Bot | None = None,
    event: OneBot11GroupMessageEvent | None = None,
) -> Any:
    if bot is None or event is None:
        return None

    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("recall_message")
    if not config.enabled:
        return await recall_message_cmd.finish(await _("该功能已禁用"))

    try:
        target_user_id, target_name, recall_count = await _resolve_recall_args(
            target,
            count,
            bot,
            event,
        )
    except ValueError as e:
        logger.warning(f"解析用户失败: {e}")
        return await recall_message_cmd.finish(str(e))

    if recall_count < 1:
        return await recall_message_cmd.finish(await _("撤回数量不能小于 1 条"))
    if recall_count > RECALL_COUNT_MAX:
        return await recall_message_cmd.finish(
            (await _("撤回数量不能超过 {max} 条")).format(max=RECALL_COUNT_MAX)
        )

    if not await check_bot_privilege(bot, event.group_id, recall_message_cmd):
        return None

    records = await _list_recall_candidate_records(
        bot,
        event,
        target_user_id=target_user_id,
        recall_count=recall_count,
    )
    result = await _recall_records(
        bot,
        event,
        records,
        target_user_id=target_user_id,
        recall_count=recall_count,
    )

    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="recall_message",
            target_user_id=target_user_id,
            reason=(
                f"count={recall_count}, recalled={result.recalled}, "
                f"skipped={result.skipped}, failed={result.failed}"
            ),
        ),
    )

    target_text = ""
    if target_user_id is not None:
        target_text = "\n" + (await _("目标: {target}")).format(
            target=format_user_display_name(target_user_id, target_name)
        )
    message = await _(
        "已撤回 {recalled} 条消息，跳过 {skipped} 条，失败 {failed} 条{target_text}"
    )
    return await recall_message_cmd.finish(
        message.format(
            recalled=result.recalled,
            skipped=result.skipped,
            failed=result.failed,
            target_text=target_text,
        )
    )
