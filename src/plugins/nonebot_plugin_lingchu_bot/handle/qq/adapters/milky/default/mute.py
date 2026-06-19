from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_alconna.uniseg import At

from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    whole_mute_cmd,
    whole_unmute_cmd,
)
from .common import resolve_user_milky

# 禁言时长范围限制（秒）
_MUTE_DURATION_MIN = 1
_MUTE_DURATION_MAX = 30 * 24 * 60 * 60  # 30 天


def _bot_self_id_safe(bot: MilkyBot) -> int | None:
    """安全获取机器人 self_id，无法转换时返回 None"""
    try:
        return int(bot.self_id)
    except (ValueError, TypeError):
        return None


@selected_adapter_handle(member_mute_cmd, "~milky", "member_mute")
async def milkybot_mute(  # noqa: PLR0911
    user: At | int,
    duration: int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 1. 参数合法性检查
    if duration < _MUTE_DURATION_MIN:
        return await member_mute_cmd.finish(
            (await _("禁言时长不能小于 {min} 秒")).format(min=_MUTE_DURATION_MIN)
        )
    if duration > _MUTE_DURATION_MAX:
        return await member_mute_cmd.finish(
            (await _("禁言时长不能超过 {max} 秒（30天）")).format(
                max=_MUTE_DURATION_MAX
            )
        )

    # 2. 解析用户
    try:
        target_user_id, target_name = await resolve_user_milky(user, bot, event)
    except ValueError as e:
        logger.warning(f"解析用户失败: {e}")
        return await member_mute_cmd.finish(str(e))

    # 3. 边界条件检查
    if target_user_id == event.data.sender.user_id:
        return await member_mute_cmd.finish(await _("不能禁言自己"))

    bot_self_id = _bot_self_id_safe(bot)
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await member_mute_cmd.finish(await _("不能禁言机器人"))

    # 4. 执行禁言操作
    try:
        await bot.set_group_member_mute(
            group_id=event.data.peer_id, user_id=target_user_id, duration=duration
        )
    except NetworkError as e:
        logger.error(f"禁言失败，网络异常: {e!r}")
        return await member_mute_cmd.finish(await _("禁言失败，网络异常"))
    except ActionFailed as e:
        logger.error(f"禁言失败，操作被拒绝: {e!r}")
        return await member_mute_cmd.finish(await _("禁言失败，操作被拒绝"))

    # 5. 格式化反馈消息
    reason_text = await _("违反群规「默认」") if reason is None else reason
    name_display = f"@{target_name}" if target_name else str(target_user_id)
    msg = (
        await _(
            "已禁言: \n"
            "名称: {name_display}\n"
            "时长: {duration} 秒\n"
            "原因: {reason}\n"
            "标识: {target_user_id}"
        )
    ).format(
        name_display=name_display,
        duration=duration,
        reason=reason_text,
        target_user_id=target_user_id,
    )
    return await member_mute_cmd.finish(message=UniMessage(message=msg))


@selected_adapter_handle(whole_mute_cmd, "~milky", "whole_mute")
async def milkybot_whole_mute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    try:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=True)
    except NetworkError as e:
        logger.error(f"全体禁言失败，网络异常: {e!r}")
        return await whole_mute_cmd.finish(await _("全体禁言失败，网络异常"))
    except ActionFailed as e:
        logger.error(f"全体禁言失败，操作被拒绝: {e!r}")
        return await whole_mute_cmd.finish(await _("全体禁言失败，操作被拒绝"))

    return await whole_mute_cmd.finish(await _("全体禁言成功"))


@selected_adapter_handle(member_unmute_cmd, "~milky", "member_unmute")
async def milkybot_unmute(
    user: At | int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 1. 解析用户
    try:
        target_user_id, target_name = await resolve_user_milky(user, bot, event)
    except ValueError as e:
        logger.warning(f"解析用户失败: {e}")
        return await member_unmute_cmd.finish(str(e))

    # 2. 边界条件检查
    if target_user_id == event.data.sender.user_id:
        return await member_unmute_cmd.finish(await _("不能解禁自己"))

    bot_self_id = _bot_self_id_safe(bot)
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await member_unmute_cmd.finish(await _("不能解禁机器人"))

    # 3. 执行解禁操作
    try:
        await bot.set_group_member_mute(
            group_id=event.data.peer_id, user_id=target_user_id, duration=0
        )
    except NetworkError as e:
        logger.error(f"解禁失败，网络异常: {e!r}")
        return await member_unmute_cmd.finish(await _("解禁失败，网络异常"))
    except ActionFailed as e:
        logger.error(f"解禁失败，操作被拒绝: {e!r}")
        return await member_unmute_cmd.finish(await _("解禁失败，操作被拒绝"))

    # 4. 格式化反馈消息
    reason_text = await _("管理员操作「默认」") if reason is None else reason
    name_display = f"@{target_name}" if target_name else str(target_user_id)
    msg = (
        await _(
            "已解禁: \n名称: {name_display}\n原因: {reason}\n标识: {target_user_id}"
        )
    ).format(
        name_display=name_display,
        reason=reason_text,
        target_user_id=target_user_id,
    )
    return await member_unmute_cmd.finish(message=UniMessage(message=msg))


@selected_adapter_handle(whole_unmute_cmd, "~milky", "whole_unmute")
async def milkybot_whole_unmute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    try:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=False)
    except NetworkError as e:
        logger.error(f"全体解禁失败，网络异常: {e!r}")
        return await whole_unmute_cmd.finish(await _("全体解禁失败，网络异常"))
    except ActionFailed as e:
        logger.error(f"全体解禁失败，操作被拒绝: {e!r}")
        return await whole_unmute_cmd.finish(await _("全体解禁失败，操作被拒绝"))

    return await whole_unmute_cmd.finish(await _("全体解禁成功"))
