from typing import TYPE_CHECKING, Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_alconna.uniseg import At

from .....i18n import _async as _
from ..common import selected_adapter_handle
from ..mute import member_mute_cmd, member_unmute_cmd, whole_mute_cmd, whole_unmute_cmd

if TYPE_CHECKING:
    from nonebot_plugin_alconna.uniseg.segment import Text


@selected_adapter_handle(member_mute_cmd, "~milky")
async def milkybot_mute(
    user: At,
    duration: int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    reason: str | None = None,
) -> Any:
    target_user_id = int(user.target)
    mention: dict | None = next(
        (item for item in event.data.segments if item.get("type") == "mention"), None
    )
    if mention:
        target_user_id: int = mention["data"]["user_id"]
        target_name: str | None = mention["data"]["name"]
    else:
        target_name: str | None = user.display or ""
    reason_text = await _("违反群规「默认」") if reason is None else reason

    try:
        await bot.set_group_member_mute(
            group_id=event.data.peer_id, user_id=target_user_id, duration=duration
        )
    except NetworkError as e:
        logger.error(f"禁言失败，网络异常: {e!r}")
        return await member_mute_cmd.finish(
            message=(await _("禁言失败，网络异常: {error!r}")).format(error=e)
        )
    except ActionFailed as e:
        logger.error(f"禁言失败，操作被拒绝: {e}")
        return await member_mute_cmd.finish(
            message=(await _("禁言失败，操作被拒绝: {error}")).format(error=e)
        )

    msg = (
        await _(
            "已禁言: \n"
            "名称: @{target_name}\n"
            "时长: {duration} 秒\n"
            "原因: {reason}\n"
            "标识: {target_user_id}"
        )
    ).format(
        target_name=target_name,
        duration=duration,
        reason=reason_text,
        target_user_id=target_user_id,
    )
    return await member_mute_cmd.finish(message=UniMessage(message=msg))


@selected_adapter_handle(whole_mute_cmd, "~milky")
async def milkybot_whole_mute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    try:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=True)
    except NetworkError as e:
        logger.error(f"全体禁言失败，网络异常: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=(await _("全体禁言失败，网络异常: {error!r}")).format(error=e)
        )
        return await whole_mute_cmd.finish(message=await msg.export(bot))
    except ActionFailed as e:
        logger.error(f"全体禁言失败，操作被拒绝: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=(await _("全体禁言失败，操作被拒绝: {error!r}")).format(error=e)
        )
        return await whole_mute_cmd.finish(message=await msg.export(bot))

    logger.info("全体禁言成功")
    msg: UniMessage[Text] = UniMessage(message=await _("全体禁言成功"))
    return await whole_mute_cmd.finish(message=await msg.export(bot))


@selected_adapter_handle(member_unmute_cmd, "~milky")
async def milkybot_unmute(
    user: At,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    reason: str | None = None,
) -> Any:
    target_user_id = int(user.target)
    mention: dict | None = next(
        (item for item in event.data.segments if item.get("type") == "mention"), None
    )
    if mention:
        target_user_id: int = mention["data"]["user_id"]
        target_name: str | None = mention["data"]["name"]
    else:
        target_name: str | None = user.display or ""
    reason_text = await _("管理员操作「默认」") if reason is None else reason

    try:
        await bot.set_group_member_mute(
            group_id=event.data.peer_id, user_id=target_user_id, duration=0
        )
    except NetworkError as e:
        logger.error(f"解禁失败，网络异常: {e!r}")
        return await member_unmute_cmd.finish(
            message=(await _("解禁失败，网络异常: {error!r}")).format(error=e)
        )
    except ActionFailed as e:
        logger.error(f"解禁失败，操作被拒绝: {e!r}")
        return await member_unmute_cmd.finish(
            message=(await _("解禁失败，操作被拒绝: {error!r}")).format(error=e)
        )

    msg: UniMessage[Text] = UniMessage(
        message=(
            await _(
                "已解禁: \n名称: {target_name}\n原因: {reason}\n标识: {target_user_id}"
            )
        ).format(
            target_name=target_name,
            reason=reason_text,
            target_user_id=target_user_id,
        )
    )
    logger.info(msg)
    return await member_unmute_cmd.finish(message=msg)


@selected_adapter_handle(whole_unmute_cmd, "~milky")
async def milkybot_whole_unmute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    try:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=False)
    except NetworkError as e:
        logger.error(f"全体解禁失败，网络异常: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=(await _("全体解禁失败，网络异常: {error!r}")).format(error=e)
        )
        return await whole_unmute_cmd.finish(message=await msg.export(bot))
    except ActionFailed as e:
        logger.error(f"全体解禁失败，操作被拒绝: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=(await _("全体解禁失败，操作被拒绝: {error!r}")).format(error=e)
        )
        return await whole_unmute_cmd.finish(message=await msg.export(bot))

    logger.info("全体解禁成功")
    msg: UniMessage[Text] = UniMessage(message=await _("全体解禁成功"))
    return await whole_unmute_cmd.finish(message=await msg.export(bot))
