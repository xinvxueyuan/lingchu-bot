from typing import TYPE_CHECKING, Any

from arclet.alconna import Alconna, Args
from nonebot import logger

# from nonebot.adapters.discord import Bot as DiscordBot
# from nonebot.adapters.discord import MessageEvent as DiscordEvent
# from nonebot.adapters.github import Bot as GitHubBot
# from nonebot.adapters.github import Event as GitHubEvent
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.internal.matcher.matcher import Matcher

# from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
# from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11Event
# from nonebot.adapters.onebot.v12 import Bot as OneBotV12Bot
# from nonebot.adapters.onebot.v12 import MessageEvent as OneBotV12Event
# from nonebot.adapters.telegram import Bot as TelegramBot
# from nonebot.adapters.telegram import Event as TelegramEvent
from nonebot_plugin_alconna import AlconnaMatcher, UniMessage, on_alconna
from nonebot_plugin_alconna.uniseg import At

from ...i18n import _

if TYPE_CHECKING:
    from nonebot_plugin_alconna.uniseg.segment import Text

member_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        "禁言",
        Args["user", At]["duration?", int, 60]["reason?", str, None],
    ),
    aliases={"禁言用户", "禁言群成员", "禁言成员", "禁", "封禁"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
whole_mute_cmd: type[Matcher] = on_alconna(
    command=Alconna(
        "全员禁言",
    ),
    aliases={
        "开启全体禁言",
        "全禁",
        "全禁言",
        "全体禁言",
        "全体禁言开启",
        "全员禁言开启",
        "开启全员禁言",
        "禁言群",
    },
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
member_unmute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        "解禁",
        Args["user", At]["reason?", str, None],
    ),
    aliases={
        "解禁用户",
        "解禁群成员",
        "解禁成员",
        "解禁",
        "解封",
        "解除封禁",
        "解除禁言",
    },
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

whole_unmute_cmd: type[Matcher] = on_alconna(
    command=Alconna(
        "全体解禁",
    ),
    aliases={
        "全员解禁",
        "关闭全体禁言",
        "解除全体禁言",
        "解禁全体",
        "解禁全员",
        "全解",
        "全解禁",
        "全体解禁",
        "关闭全员禁言",
        "解除全员禁言",
        "解禁群",
    },
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


@member_mute_cmd.handle()
async def milkybot_mute(
    user: At,
    duration: int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    reason: str | None = None,
) -> Any:
    from nonebot.adapters.milky.exception import ActionFailed, NetworkError

    target_user_id = int(user.target)
    mention: dict | None = next(
        (item for item in event.data.segments if item.get("type") == "mention"), None
    )
    if mention:
        target_user_id: int = mention["data"]["user_id"]
        target_name: str | None = mention["data"]["name"]
    else:
        target_name: str | None = user.display or ""
    reason_text = _("违反群规「默认」") if reason is None else reason

    try:
        await bot.set_group_member_mute(
            group_id=event.data.peer_id, user_id=target_user_id, duration=duration
        )
    except NetworkError as e:
        logger.error(f"禁言失败，网络异常: {e!r}")
        return await member_mute_cmd.finish(
            message=_("禁言失败，网络异常: {error!r}").format(error=e)
        )
    except ActionFailed as e:
        logger.error(f"禁言失败，操作被拒绝: {e}")
        return await member_mute_cmd.finish(
            message=_("禁言失败，操作被拒绝: {error}").format(error=e)
        )

    msg = _(
        "已禁言: \n"
        "名称: @{target_name}\n"
        "时长: {duration} 秒\n"
        "原因: {reason}\n"
        "标识: {target_user_id}"
    ).format(
        target_name=target_name,
        duration=duration,
        reason=reason_text,
        target_user_id=target_user_id,
    )
    return await member_mute_cmd.finish(message=UniMessage(message=msg))


@whole_mute_cmd.handle()
async def milkybot_whole_mute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    from nonebot.adapters.milky.exception import ActionFailed, NetworkError

    try:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=True)
    except NetworkError as e:
        logger.error(f"全体禁言失败，网络异常: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=_("全体禁言失败，网络异常: {error!r}").format(error=e)
        )
        return await whole_mute_cmd.finish(message=await msg.export(bot))
    except ActionFailed as e:
        logger.error(f"全体禁言失败，操作被拒绝: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=_("全体禁言失败，操作被拒绝: {error!r}").format(error=e)
        )
        return await whole_mute_cmd.finish(message=await msg.export(bot))

    logger.info("全体禁言成功")
    msg: UniMessage[Text] = UniMessage(message=_("全体禁言成功"))
    return await whole_mute_cmd.finish(message=await msg.export(bot))


@member_unmute_cmd.handle()
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
    reason_text = _("管理员操作「默认」") if reason is None else reason
    from nonebot.adapters.milky.exception import ActionFailed, NetworkError

    try:
        await bot.set_group_member_mute(
            group_id=event.data.peer_id, user_id=target_user_id, duration=0
        )
    except NetworkError as e:
        logger.error(f"解禁失败，网络异常: {e!r}")
        return await member_unmute_cmd.finish(
            message=_("解禁失败，网络异常: {error!r}").format(error=e)
        )
    except ActionFailed as e:
        logger.error(f"解禁失败，操作被拒绝: {e!r}")
        return await member_unmute_cmd.finish(
            message=_("解禁失败，操作被拒绝: {error!r}").format(error=e)
        )

    msg: UniMessage[Text] = UniMessage(
        message=_(
            "已解禁: \n名称: {target_name}\n原因: {reason}\n标识: {target_user_id}"
        ).format(
            target_name=target_name,
            reason=reason_text,
            target_user_id=target_user_id,
        )
    )
    logger.info(msg)
    return await member_unmute_cmd.finish(message=msg)


@whole_unmute_cmd.handle()
async def milkybot_whole_unmute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    from nonebot.adapters.milky.exception import ActionFailed, NetworkError

    try:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=False)
    except NetworkError as e:
        logger.error(f"全体解禁失败，网络异常: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=_("全体解禁失败，网络异常: {error!r}").format(error=e)
        )
        return await whole_unmute_cmd.finish(message=await msg.export(bot))
    except ActionFailed as e:
        logger.error(f"全体解禁失败，操作被拒绝: {e!r}")
        msg: UniMessage[Text] = UniMessage(
            message=_("全体解禁失败，操作被拒绝: {error!r}").format(error=e)
        )
        return await whole_unmute_cmd.finish(message=await msg.export(bot))

    logger.info("全体解禁成功")
    msg: UniMessage[Text] = UniMessage(message=_("全体解禁成功"))
    return await whole_unmute_cmd.finish(message=await msg.export(bot))


async def import_handle() -> Any:
    logger.debug(_("导入mute处理器..."))
