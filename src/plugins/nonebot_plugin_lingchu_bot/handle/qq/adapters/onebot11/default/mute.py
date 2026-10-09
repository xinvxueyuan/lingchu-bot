import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import re
import time
from typing import Any

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import (
    ActionFailed as OneBot11ActionFailed,
    NetworkError as OneBot11NetworkError,
)
from nonebot.exception import ApiNotAvailable

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from ......core.config import get_handle_config_manager, plugin_config
from ......core.handle_default_values import update_handle_default
from ......database.orm_crud import DatabaseError
from ......i18n import _async as _, gettext
from ......permissions.subject_policy import find_active_subject_policy
from ......repositories import message_store as message_repository
from ....commands.common import selected_adapter_handle
from ....commands.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    mute_list_cmd,
    one_click_unmute_cmd,
    recall_message_cmd,
    set_default_mute_duration_cmd,
    whole_mute_cmd,
    whole_unmute_cmd,
)
from ..llbot.mute_list import (
    LLBOT_APP_NAME,
    MutedMember,
    fetch_group_shut_list,
)
from .common import (
    MUTE_DURATION_MAX,
    MUTE_DURATION_MIN,
    ONEBOT_V11_ADAPTER_ID,
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

#: 一对一报告里最多逐条列出的成员数；超出只影响显示，不影响已执行的动作。
UNMUTE_REPORT_MAX_LINES = 30


async def _resolve_shut_list_action(
    bot: OneBot11Bot,
) -> tuple[Any | None, str | None]:
    """解析协议端，返回可用的「被禁言名单」私有实现。

    ``default/`` 在这里只负责**解析与分派**；真正的私有接口调用在
    ``../llbot/mute_list.py``。未知协议端返回错误文案而不是猜实现 ——
    ``get_group_shut_list`` 不是 OneBot V11 标准接口，只有明确支持的协议端才有。

    版本查询本身也会失败（断连/超时），此时如实返回错误文案，不让异常冒到
    命令层导致「零回执」。
    """
    try:
        version_info = await bot.get_version_info()
    except (OneBot11ActionFailed, OneBot11NetworkError, ApiNotAvailable) as e:
        logger.warning(f"查询协议端版本失败: {type(e).__name__}: {e!r}")
        return None, await _("查询协议端版本失败")
    # OneBot V11 适配器解包响应，get_version_info() 直接返回 data 字段
    data = version_info.get("data", version_info)

    if data.get("protocol_version") != "v11":
        return None, await _("不支持的 OneBot 协议版本")

    match data.get("app_name"):
        case app_name if app_name == LLBOT_APP_NAME:
            # 该私有接口目前未发现需要版本门控（NapCat 的公告接口才有 4.18.0 门控）
            return fetch_group_shut_list, None
        case _:
            return None, await _("当前协议端不支持查询禁言名单")


async def _batch_unmute(
    bot: OneBot11Bot,
    *,
    group_id: int,
    members: list[MutedMember],
) -> tuple[list[MutedMember], list[MutedMember]]:
    """逐个解禁，返回 (成功, 失败)。

    顺序执行而非并发：群管理接口有频率限制，一把并发容易触发平台静默拒绝
    （表现为「调用成功但没生效」），排查成本高。

    单个成员失败**不中断**后续，也**不重试** —— 否则一人异常会让剩下的人永远
    解不掉，而重试会把「平台静默拒绝」误当抖动反复打。

    捕获 ``ApiNotAvailable``（连接不可用，不属于上面两者）：它若不捕获会逃逸并
    中断整批，用户只看到无回执。捕获后仍按「该成员失败」记录 —— 连接不可用时
    后续成员也会一并失败，报告会如实体现。
    """
    succeeded: list[MutedMember] = []
    failed: list[MutedMember] = []
    for member in members:
        try:
            await bot.set_group_ban(
                group_id=group_id,
                user_id=member.user_id,
                duration=0,
            )
        except (OneBot11ActionFailed, OneBot11NetworkError, ApiNotAvailable) as e:
            logger.warning(
                "解禁失败 user_id={} name={}: {}: {}",
                member.user_id,
                member.display_name,
                type(e).__name__,
                e,
            )
            failed.append(member)
        else:
            succeeded.append(member)
    return succeeded, failed


async def _detect_re_muted(
    action: Any,
    *,
    bot: OneBot11Bot,
    group_id: int,
    succeeded: list[MutedMember],
) -> list[MutedMember]:
    """解禁完成后再拉一次名单，找出「操作期间被他人再次禁言」的成员。

    为什么查：`set_group_ban(duration=0)` 之后，别人可以立刻重新禁言该成员。那种
    情况我们确实解禁成功，但**当前仍处于禁言状态** —— 报告若只说「成功」会误导
    操作者。这里多做一次查询（不是每成员一次），如实把这些人单独列出来。

    只报「我们解禁成功、复查时又出现在名单里」的人（取 ``succeeded`` 交集），
    因为只有他们的状态变化可能与本次操作有关。

    复查失败（接口不支持/网络异常）时返回空表并记日志：不能为了一段提示而让已经
    完成的解禁操作变成「报错」。
    """
    if not succeeded:
        return []
    try:
        after = await action(bot=bot, group_id=group_id)
    except (OneBot11ActionFailed, OneBot11NetworkError, ApiNotAvailable) as e:
        logger.warning(
            f"解禁后复查禁言名单失败（不影响结果）: {type(e).__name__}: {e!r}"
        )
        return []
    still_muted = {m.user_id for m in after}
    return [m for m in succeeded if m.user_id in still_muted]


def _format_unmute_report(
    *,
    succeeded: list[MutedMember],
    failed: list[MutedMember],
    re_muted: list[MutedMember] | None = None,
) -> str:
    """按「成员一对一」格式拼报告：每人一行，带成功/失败标记。

    只负责排版，不改变事实 —— **失败者必须出现且带失败标记**。

    展示优先级（低者先被截断）：成功 → 失败 → 「操作期间被他人再次禁言」。
    后两者是可操作信息，**不能被成功行挤掉**；若它们本身就超出上限，则先保失败、
    再保再次禁言，其余截断并注明。``re_muted`` 是 ``succeeded`` 的子集，由调用方
    从「解禁后的名单」里挑出来，这里只负责呈现，不重复计入成功行。

    标签与尾注都走 i18n，避免英文 locale 下混出中文。
    """
    failed_lines = [
        f"❌ {format_user_display_name(m.user_id, m.display_name, style='detail')}"
        for m in failed
    ]
    re_muted_list = list(re_muted or [])
    re_muted_lines = [
        f"⚠️ {format_user_display_name(m.user_id, m.display_name, style='detail')}"
        for m in re_muted_list
    ]
    re_muted_header = (
        gettext(
            "以下 {count} 人在操作期间被他人再次禁言（已解禁，但当前仍被禁言）："
        ).format(count=len(re_muted_lines))
        if re_muted_lines
        else ""
    )
    succeeded_lines = [
        f"✅ {format_user_display_name(m.user_id, m.display_name, style='detail')}"
        for m in succeeded
    ]

    # 必需展示的行（失败 + 再次禁言 + 再次禁言的标题行）
    required = len(failed_lines) + len(re_muted_lines) + (1 if re_muted_header else 0)
    if required >= UNMUTE_REPORT_MAX_LINES:
        total = len(failed_lines) + len(re_muted_lines) + len(succeeded_lines)
        shown = failed_lines + re_muted_lines
        budget = UNMUTE_REPORT_MAX_LINES - 1
        shown = shown[:budget]
        shown.append(
            gettext("...另有 {extra} 人未列出（共 {total} 人）").format(
                extra=total - len(shown), total=total
            )
        )
        return "\n".join(shown)

    budget = UNMUTE_REPORT_MAX_LINES - required
    lines = succeeded_lines[:budget]
    omitted = len(succeeded_lines) - len(lines)
    lines.extend(failed_lines)
    if re_muted_header:
        lines.append(re_muted_header)
        lines.extend(re_muted_lines)
    if omitted:
        total = len(succeeded_lines) + len(failed_lines) + len(re_muted_lines)
        lines.append(
            gettext("...另有 {omitted} 名成功者未列出（共 {total} 人）").format(
                omitted=omitted, total=total
            )
        )
    return "\n".join(lines)


#: 审计 ``data_summary`` 里可能出现的键；解析时按这些键切分。
_AUDIT_SUMMARY_KEYS = ("operator", "target", "action", "group", "duration", "reason")

#: 生成格式里 ``reason`` 之后的字段名不再解析（它是最后一个字段）。
_AUDIT_TERMINAL_KEY = "reason"

#: 「禁言列表」逐条列出的成员上限；超出只影响显示。
MUTE_LIST_REPORT_MAX_LINES = 30

#: 判定「这条审计是否对应当前这次禁言」的容差（秒）。
#: ``shutUpTime`` 由协议端/QQ 侧时钟算出，审计 ``created_at`` 是我们本地时钟，
#: 两者存在偏差，因此允许一定容差；超出容差即视为**上一轮遗留**记录，按「未知」显示。
MUTE_AUDIT_END_TOLERANCE_SECONDS = 60


def _parse_mute_audit_summary(summary: str | None) -> dict[str, str]:
    """解析命令审计的自由文本 ``data_summary``。

    格式形如 ``operator=1, target=2, action=member_mute, group=3, duration=60,
    reason=刷屏, 重复``。**不能**按 ``, `` 简单切分 —— reason 本身可能含逗号。

    做法：按已知键名定位，值延伸到"下一个 ``键=`` 出现处"之前；而 ``reason`` 是
    生成格式里的**最后一个**字段，其后的全部文本都归它 —— 否则原因里出现形如
    ``target=`` / ``duration=`` 的片断时会被当成新字段，导致原因被截断、
    甚至凭空多出一个假字段。
    """
    if not summary:
        return {}

    # 找到每个已知键的出现位置（要求前一个字符是行首/空格/逗号，避免匹配到值的内部）
    marks: list[tuple[int, str]] = [
        (m.start(), key)
        for key in _AUDIT_SUMMARY_KEYS
        for m in re.finditer(rf"(?:^|(?<=[,\s])){re.escape(key)}=", summary)
    ]
    if not marks:
        return {}
    marks.sort()

    # reason 之后的"键"都只是原因文本，不再解析
    terminal_idx = next(
        (i for i, (_, key) in enumerate(marks) if key == _AUDIT_TERMINAL_KEY),
        None,
    )
    if terminal_idx is not None:
        marks = marks[: terminal_idx + 1]

    parsed: dict[str, str] = {}
    for idx, (start, key) in enumerate(marks):
        value_start = start + len(key) + 1
        if key == _AUDIT_TERMINAL_KEY:
            end = len(summary)
        else:
            end = marks[idx + 1][0] if idx + 1 < len(marks) else len(summary)
        value = summary[value_start:end].strip().rstrip(",").strip()
        # 先出现的键优先（同一 target 只留第一条）
        parsed.setdefault(key, value)
    return parsed


def _format_remaining(seconds: int) -> str:
    """把剩余秒数格式化；已到期显示 0 秒，不显示负数。

    单位走 i18n（中文：天/小时/分/秒；英文：d/h/m/s）。
    """
    unit_sec, unit_min = gettext("秒"), gettext("分")
    unit_hour, unit_day = gettext("小时"), gettext("天")

    if seconds <= 0:
        return f"0 {unit_sec}"
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)

    if days:
        return (
            f"{days} {unit_day} {hours} {unit_hour}" if hours else f"{days} {unit_day}"
        )
    if hours:
        return (
            f"{hours} {unit_hour} {minutes} {unit_min}"
            if minutes
            else f"{hours} {unit_hour}"
        )
    if minutes:
        return (
            f"{minutes} {unit_min} {secs} {unit_sec}"
            if secs
            else f"{minutes} {unit_min}"
        )
    return f"{secs} {unit_sec}"


def _audit_matches_current_mute(
    audit: dict[str, str],
    *,
    created_at_ts: float | None,
    shut_up_time: int | None,
) -> bool:
    """这条审计是否描述**当前这次**禁言。

    判据：审计（下达时刻 ``created_at`` + ``duration``）推算出的解禁时刻，应与当前
    禁言的 ``shut_up_time`` 一致（容差见 :data:`MUTE_AUDIT_END_TOLERANCE_SECONDS`）。
    不一致说明成员被解除后又被别人重新禁言（本轮没有对应审计），此时**不能**把上一
    轮的原因当作现在的原因显示 —— 按「未知」降级。

    缺 ``duration`` 或 ``shut_up_time`` 时无法确认，返回 ``False``（宁缺勿猜）。
    """
    if shut_up_time is None or created_at_ts is None:
        return False
    raw_duration = audit.get("duration")
    if raw_duration is None:
        return False
    try:
        duration = int(raw_duration)
    except ValueError:
        return False
    expected_end = created_at_ts + duration
    return abs(expected_end - shut_up_time) <= MUTE_AUDIT_END_TOLERANCE_SECONDS


def _format_mute_list_report(
    *,
    members: list[MutedMember],
    audit_by_target: dict[int, dict[str, str]],
    now_ts: int,
) -> str:
    """按「成员一对一」格式拼禁言列表。

    每行形如 ``甲(10001) — 剩余 12 分 30 秒 · 原因: 刷屏``。
    取不到原因/剩余时间时显示占位，**不留空也不猜**。整行走 i18n。
    """
    unknown_reason = gettext("未知（非本机器人操作或记录已过保留期）")
    unknown_remaining = gettext("未知")
    line_template = gettext("{name} — 剩余 {remaining} · 原因: {reason}")

    lines: list[str] = []
    for member in members:
        remaining = (
            unknown_remaining
            if member.shut_up_time is None
            else _format_remaining(member.shut_up_time - now_ts)
        )
        audit = audit_by_target.get(member.user_id, {})
        reason = audit.get("reason") or unknown_reason
        name = format_user_display_name(
            member.user_id, member.display_name, style="detail"
        )
        lines.append(
            line_template.format(name=name, remaining=remaining, reason=reason)
        )

    total = len(lines)
    if total > MUTE_LIST_REPORT_MAX_LINES:
        lines = lines[:MUTE_LIST_REPORT_MAX_LINES]
        lines.append(
            gettext("...另有 {extra} 人未列出（共 {total} 人）").format(
                extra=total - MUTE_LIST_REPORT_MAX_LINES, total=total
            )
        )
    return "\n".join(lines)


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
    except OneBot11NetworkError as e:
        logger.warning(f"撤回校验网络异常: message_id={message_id}, error={e!r}")
        return None
    if not _message_type_matches(message) or not _group_id_matches(message, group_id):
        return None
    sender_id = _sender_id_from_message(message)
    if target_user_id is not None and sender_id != target_user_id:
        return None
    return message


async def _is_recall_protected_target(
    session: async_scoped_session,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    target_user_id: int,
) -> bool:
    if "recall_message" not in plugin_config.protected_subject_feature_keys:
        return False
    protected = await find_active_subject_policy(
        session,
        policy_type="protected",
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id=bot_id(bot),
        group_id=event.group_id,
        user_id=target_user_id,
    )
    return protected is not None


async def _can_recall_sender(
    session: async_scoped_session,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    sender_id: int,
    *,
    sender_decisions: dict[int, bool] | None = None,
) -> bool:
    """Return True when messages from sender_id may be recalled.

    Fail closed: when the sender's role cannot be verified (API failure),
    skip the recall instead of potentially recalling an admin/owner message.
    """
    if sender_id == event.user_id:
        return False
    bot_self = bot_self_id_safe(bot)
    if bot_self is not None and sender_id == bot_self:
        return False
    if sender_decisions is not None and sender_id in sender_decisions:
        return sender_decisions[sender_id]
    decision = await _evaluate_recall_sender(session, bot, event, sender_id)
    if sender_decisions is not None:
        sender_decisions[sender_id] = decision
    return decision


async def _evaluate_recall_sender(
    session: async_scoped_session,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    sender_id: int,
) -> bool:
    if await _is_recall_protected_target(session, bot, event, sender_id):
        return False
    try:
        member_info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=sender_id,
            no_cache=True,
        )
    except OneBot11ActionFailed:
        logger.warning(
            f"无法确认发送者角色，跳过撤回: group_id={event.group_id}, "
            f"sender_id={sender_id}"
        )
        return False
    except OneBot11NetworkError as e:
        logger.warning(
            f"查询发送者角色网络异常，跳过撤回: group_id={event.group_id}, "
            f"sender_id={sender_id}, error={e!r}"
        )
        return False
    return member_info.get("role", "member") not in ("admin", "owner")


def _candidate_fetch_limit(count: int) -> int:
    return min(max(count * 5, count + 20), 500)


def _record_conversation_id(record: Any) -> str | None:
    value = getattr(record, "conversation_id", None)
    return value if isinstance(value, str) else None


async def _record_raw_event(record: Any) -> dict[str, Any] | None:
    raw_event = getattr(record, "raw_event", None)
    if not isinstance(raw_event, str):
        return None
    try:
        parsed = await asyncio.to_thread(json.loads, raw_event)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


async def _record_belongs_to_group(record: Any, group_id: int) -> bool:
    group_id_text = str(group_id)
    conversation_id = _record_conversation_id(record)
    if conversation_id == group_id_text:
        return True
    if conversation_id is not None and conversation_id.startswith(
        f"group_{group_id_text}_"
    ):
        return True
    raw_event = await _record_raw_event(record)
    if raw_event is None:
        return False
    return _message_id_int(raw_event.get("group_id")) == group_id


async def _merge_recall_candidates(
    *record_groups: list[Any],
    group_id: int,
) -> list[Any]:
    records: list[Any] = []
    seen: set[str] = set()
    for group in record_groups:
        for record in group:
            message_id = getattr(record, "message_id", None)
            key = str(message_id) if message_id is not None else f"id:{id(record)}"
            if key in seen or not await _record_belongs_to_group(record, group_id):
                continue
            seen.add(key)
            records.append(record)
    return records


async def _list_recall_candidate_records(
    session: async_scoped_session,
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
        session,
        **common_filters,
        limit=min(fetch_limit * 2, 500),
    )
    group_records = await message_repository.list_recent_messages(
        session,
        **common_filters,
        conversation_id=str(event.group_id),
        limit=fetch_limit,
    )
    return await _merge_recall_candidates(
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
    session: async_scoped_session,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    record: Any,
    *,
    trigger_message_id: str,
    target_user_id: int | None,
    sender_decisions: dict[int, bool],
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
    if sender_id is None or not await _can_recall_sender(
        session, bot, event, sender_id, sender_decisions=sender_decisions
    ):
        return "skipped"
    try:
        await bot.delete_msg(message_id=message_id)
    except OneBot11ActionFailed as e:
        logger.warning(f"撤回失败: message_id={message_id}, error={e!r}")
        return "failed"
    except OneBot11NetworkError as e:
        logger.warning(f"撤回网络异常: message_id={message_id}, error={e!r}")
        return "failed"
    return "recalled"


async def _recall_records(
    session: async_scoped_session,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    records: list[Any],
    *,
    target_user_id: int | None,
    recall_count: int,
) -> RecallResult:
    result = RecallResult()
    trigger_message_id = str(getattr(event, "message_id", ""))
    sender_decisions: dict[int, bool] = {}
    for record in records:
        if result.recalled >= recall_count:
            break
        status = await _recall_record_message(
            session,
            bot,
            event,
            record,
            trigger_message_id=trigger_message_id,
            target_user_id=target_user_id,
            sender_decisions=sender_decisions,
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
    duration: int | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
    reason: str | None = None,
) -> Any:
    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await member_mute_cmd.finish(await _("该功能已禁用"))

    # 读取配置参数
    default_reason_text = config.defaults.get("default_reason", "管理员操作")

    actual_duration = (
        duration if duration is not None else config.defaults.get("mute_duration", 300)
    )

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

    if not await check_target_privilege(
        session, bot, event, target_user_id, member_mute_cmd
    ):
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
    # 记录**实际展示**的原因（含配置默认值）—— 只记可选参数会让「没写原因」的禁言
    # 在禁言列表里显示成「未知」，与回执自相矛盾。
    reason_text = await _(default_reason_text) if reason is None else reason
    record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="member_mute",
            target_user_id=target_user_id,
            duration=actual_duration,
            reason=reason_text,
        ),
    )

    # 7. 格式化反馈消息
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


@selected_adapter_handle(
    set_default_mute_duration_cmd, "~onebot.v11", "set_default_mute_duration"
)
async def onebot11_set_default_mute_duration(
    duration: int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    """Update the configured default duration for member mutes."""
    config_manager = get_handle_config_manager()
    config = await config_manager.get_config("member_mute")
    if not config.enabled:
        return await set_default_mute_duration_cmd.finish(await _("该功能已禁用"))
    if duration < MUTE_DURATION_MIN:
        return await set_default_mute_duration_cmd.finish(
            (await _("禁言时长不能小于 {min} 秒")).format(min=MUTE_DURATION_MIN)
        )
    if duration > MUTE_DURATION_MAX:
        return await set_default_mute_duration_cmd.finish(
            (await _("禁言时长不能超过 {max} 秒（30天）")).format(max=MUTE_DURATION_MAX)
        )

    await update_handle_default(
        "member_mute",
        "mute_duration",
        str(duration),
        config_manager=config_manager,
    )
    record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(action="set_default_mute_duration", duration=duration),
    )
    message = await _("默认禁言时长已更新为 {duration} 秒")
    return await set_default_mute_duration_cmd.finish(message.format(duration=duration))


@selected_adapter_handle(whole_mute_cmd, "~onebot.v11", "whole_mute")
async def onebot11_whole_mute(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
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
    record_audit_fire_and_forget(bot, event, CommandAudit(action="whole_mute"))

    return await whole_mute_cmd.finish(await _("全体禁言成功"))


@selected_adapter_handle(member_unmute_cmd, "~onebot.v11", "member_unmute")
async def onebot11_unmute(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
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
    record_audit_fire_and_forget(
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
    session: async_scoped_session,
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
    record_audit_fire_and_forget(bot, event, CommandAudit(action="whole_unmute"))

    return await whole_unmute_cmd.finish(await _("全体解禁成功"))


@selected_adapter_handle(one_click_unmute_cmd, "~onebot.v11", "one_click_unmute")
async def onebot11_one_click_unmute(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    """把本群当前被禁言的成员逐个解禁。

    与「全体解禁」（``whole_unmute``，关掉全群禁言开关）语义不同：这里作用于
    **逐个成员**的禁言状态。
    """
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await one_click_unmute_cmd.finish(await _("该功能已禁用"))

    if not await check_bot_privilege(bot, event.group_id, one_click_unmute_cmd):
        return None

    # 1. 解析协议端 → 取私有实现（default/ 不直接调私有 action）
    action, error = await _resolve_shut_list_action(bot)
    if error is not None or action is None:
        return await one_click_unmute_cmd.finish(
            error or await _("当前协议端不支持查询禁言名单")
        )

    try:
        members = await action(bot=bot, group_id=event.group_id)
    except (OneBot11ActionFailed, OneBot11NetworkError, ApiNotAvailable) as e:
        logger.error(f"获取禁言名单失败: {type(e).__name__}: {e!r}")
        return await one_click_unmute_cmd.finish(await _("获取禁言名单失败"))

    if not members:
        return await one_click_unmute_cmd.finish(await _("本群当前没有被禁言的成员"))

    # 2. 逐个解禁（顺序、不重试、失败不中断）
    succeeded, failed = await _batch_unmute(
        bot, group_id=event.group_id, members=members
    )

    # 3. 解禁后再拉一次名单：把「操作期间被他人重新禁言」的成员挑出来如实标出。
    #    这一步失败不影响结果呈现，只是给不出这段提示。
    re_muted = await _detect_re_muted(
        action, bot=bot, group_id=event.group_id, succeeded=succeeded
    )

    # 4. 审计（汇总：批量命令没有单一 target，至少要留下影响面）
    outcome = gettext("成功 {ok} 人，失败 {bad} 人").format(
        ok=len(succeeded) + len(re_muted), bad=len(failed)
    )
    record_audit_fire_and_forget(
        bot, event, CommandAudit(action="one_click_unmute", outcome=outcome)
    )

    # 5. 一对一报告（失败与被再次禁言都逐一列出）
    header = await _("一键解禁完成：成功 {ok} 人，失败 {bad} 人")
    re_muted_ids = {m.user_id for m in re_muted}
    body = _format_unmute_report(
        succeeded=[m for m in succeeded if m.user_id not in re_muted_ids],
        failed=failed,
        re_muted=re_muted,
    )
    return await one_click_unmute_cmd.finish(
        header.format(ok=len(succeeded) + len(re_muted), bad=len(failed))
        + "\n\n"
        + body
    )


async def _collect_mute_reasons(
    session: async_scoped_session,
    *,
    bot: OneBot11Bot,
    group_id: int,
    members: list[MutedMember],
) -> dict[int, dict[str, str]]:
    """从审计记录取回本群各成员的「原因」等字段（尽力而为）。

    只把**确实对应当前这次禁言**的记录挂上去（判据见
    :func:`_audit_matches_current_mute`）—— 成员被解除后又被别人重新禁言时，
    上一轮的原因不能被当成现在的原因显示。

    审计记录是自由文本且有保留期，取不到就返回空表让调用方降级成「未知」。
    查询失败也只降级，不影响列出成员本身。
    """
    try:
        records = await message_repository.list_recent_command_audits(
            session,
            action="member_mute",
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=bot_id(bot),
            group_id=group_id,
        )
    except DatabaseError:
        logger.exception("查询禁言审计记录失败，原因将显示为未知")
        return {}

    # 先按群号与 target 分组解析，再逐个成员挑出「对应当前禁言」的那条
    parsed_records: list[tuple[int, float | None, dict[str, str]]] = []
    group_marker = f"group={group_id}"
    for record in records:
        parsed = _parse_mute_audit_summary(record.data_summary)
        # 二次过滤：data_summary 是自由文本，只靠子串匹配会被 group=999 前缀骗过
        if parsed.get("group") != str(group_id):
            continue
        if group_marker not in (record.data_summary or ""):
            continue
        try:
            target = int(parsed["target"])
        except (KeyError, ValueError):
            continue
        created_at = getattr(record, "created_at", None)
        # 只接受真正的 datetime：拿不到就当作无法校验（宁缺勿猜），
        # 绝不让这里抛异常把整条命令带走
        created_at_ts = (
            created_at.timestamp() if isinstance(created_at, datetime) else None
        )
        parsed_records.append((target, created_at_ts, parsed))

    audit_by_target: dict[int, dict[str, str]] = {}
    for member in members:
        for target, created_at_ts, parsed in parsed_records:  # 已按时间倒序
            if target != member.user_id:
                continue
            if not _audit_matches_current_mute(
                parsed,
                created_at_ts=created_at_ts,
                shut_up_time=member.shut_up_time,
            ):
                continue
            audit_by_target[member.user_id] = parsed
            break
    return audit_by_target


@selected_adapter_handle(mute_list_cmd, "~onebot.v11", "mute_list")
async def onebot11_mute_list(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    """列出本群当前被禁言的成员及其剩余时间、原因。

    原因来自「禁言」命令留下的审计记录（自由文本、受保留期约束），
    取不到时显示占位而不是猜。
    """
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await mute_list_cmd.finish(await _("该功能已禁用"))

    if not await check_bot_privilege(bot, event.group_id, mute_list_cmd):
        return None

    action, error = await _resolve_shut_list_action(bot)
    if error is not None or action is None:
        return await mute_list_cmd.finish(
            error or await _("当前协议端不支持查询禁言名单")
        )

    try:
        members = await action(bot=bot, group_id=event.group_id)
    except (OneBot11ActionFailed, OneBot11NetworkError, ApiNotAvailable) as e:
        logger.error(f"获取禁言名单失败: {type(e).__name__}: {e!r}")
        return await mute_list_cmd.finish(await _("获取禁言名单失败"))

    if not members:
        return await mute_list_cmd.finish(await _("本群当前没有被禁言的成员"))

    audit_by_target = await _collect_mute_reasons(
        session, bot=bot, group_id=event.group_id, members=members
    )

    header = (await _("本群被禁言 {count} 人")).format(count=len(members))
    body = _format_mute_list_report(
        members=members,
        audit_by_target=audit_by_target,
        now_ts=int(time.time()),
    )
    return await mute_list_cmd.finish(header + "\n\n" + body)


@selected_adapter_handle(recall_message_cmd, "~onebot.v11", "recall_message")
async def onebot11_recall_message(
    session: async_scoped_session,
    target: At | int | None = None,
    count: int | None = None,
    bot: OneBot11Bot | None = None,
    event: OneBot11GroupMessageEvent | None = None,
) -> Any:
    if bot is None or event is None:
        logger.warning("撤回命令缺少 bot/event 依赖注入，无法执行")
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
        session,
        bot,
        event,
        target_user_id=target_user_id,
        recall_count=recall_count,
    )
    result = await _recall_records(
        session,
        bot,
        event,
        records,
        target_user_id=target_user_id,
        recall_count=recall_count,
    )

    record_audit_fire_and_forget(
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
