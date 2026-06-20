from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import At

from ......core.async_utils import fire_and_forget
from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    whole_mute_cmd,
    whole_unmute_cmd,
)
from .common import (
    MUTE_DURATION_MAX,
    MUTE_DURATION_MIN,
    bot_self_id_safe,
    check_bot_privilege,
    check_self_target,
    check_target_privilege,
    record_command_audit,
    resolve_user_onebot11,
)


@selected_adapter_handle(member_mute_cmd, "~onebot.v11", "member_mute")
async def onebot11_mute(  # noqa: PLR0911
    user: At | int,
    duration: int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 1. 参数合法性检查
    if duration < MUTE_DURATION_MIN:
        return await member_mute_cmd.finish(
            (await _("禁言时长不能小于 {min} 秒")).format(min=MUTE_DURATION_MIN)
        )
    if duration > MUTE_DURATION_MAX:
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
            group_id=event.group_id, user_id=target_user_id, duration=duration
        )
    except OneBot11ActionFailed as e:
        logger.error(f"禁言失败，操作被拒绝: {e!r}")
        return await member_mute_cmd.finish(await _("禁言失败，操作被拒绝"))

    # 6. 记录审计
    fire_and_forget(
        record_command_audit(
            bot,
            event,
            action="member_mute",
            target_user_id=target_user_id,
            duration=duration,
            reason=reason,
        ),
        name="audit:member_mute",
    )

    # 7. 格式化反馈消息
    reason_text = await _("违反群规「默认」") if reason is None else reason
    name_display = f"@{target_name}" if target_name else str(target_user_id)
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
            duration=duration,
            reason=reason_text,
            target_user_id=target_user_id,
        )
    )


@selected_adapter_handle(whole_mute_cmd, "~onebot.v11", "whole_mute")
async def onebot11_whole_mute(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
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
    fire_and_forget(
        record_command_audit(bot, event, action="whole_mute"),
        name="audit:whole_mute",
    )

    return await whole_mute_cmd.finish(await _("全体禁言成功"))


@selected_adapter_handle(member_unmute_cmd, "~onebot.v11", "member_unmute")
async def onebot11_unmute(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
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
    fire_and_forget(
        record_command_audit(
            bot, event, action="member_unmute", target_user_id=target_user_id
        ),
        name="audit:member_unmute",
    )

    # 5. 格式化反馈消息
    name_display = f"@{target_name}" if target_name else str(target_user_id)
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
    try:
        await bot.set_group_whole_ban(group_id=event.group_id, enable=False)
    except OneBot11ActionFailed as e:
        logger.error(f"全体解禁失败，操作被拒绝: {e!r}")
        return await whole_unmute_cmd.finish(await _("全体解禁失败，操作被拒绝"))

    # 记录审计
    fire_and_forget(
        record_command_audit(bot, event, action="whole_unmute"),
        name="audit:whole_unmute",
    )

    return await whole_unmute_cmd.finish(await _("全体解禁成功"))
