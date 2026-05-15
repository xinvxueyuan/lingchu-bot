from typing import TYPE_CHECKING, Any

from arclet.alconna import Alconna, Args
from nonebot import logger

# from nonebot.adapters.discord import Bot as DiscordBot
# from nonebot.adapters.discord import MessageEvent as DiscordEvent
# from nonebot.adapters.github import Bot as GitHubBot
# from nonebot.adapters.github import Event as GitHubEvent
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.message import Mention as At

# from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
# from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11Event
# from nonebot.adapters.onebot.v12 import Bot as OneBotV12Bot
# from nonebot.adapters.onebot.v12 import MessageEvent as OneBotV12Event
# from nonebot.adapters.telegram import Bot as TelegramBot
# from nonebot.adapters.telegram import Event as TelegramEvent
from nonebot_plugin_alconna import AlconnaMatcher, UniMessage, on_alconna

if TYPE_CHECKING:
    from nonebot_plugin_alconna.uniseg.segment import Text

member_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        "禁言",
        Args["user", At]["duration", int, 1 * 60]["reason?", str, "违反群规"],
    ),
    aliases={
        "禁言用户",
        "禁言群成员",
        "禁言成员",
        "禁言",
        "禁",
        "封禁用户",
        "封禁群成员",
        "封禁成员",
        "封禁",
    },
    priority=5,
    block=True,
)
whole_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("全体禁言", Args["status?", bool, True]),
    aliases={
        "全员禁言",
        "开启全体禁言",
        "全禁",
        "全体禁言",
        "全体禁言开启",
        "全员禁言开启",
        "开启全员禁言",
        "禁言群",
    },
    priority=5,
    block=True,
)
member_unmute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        "解禁",
        Args["user", At],
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
)

whole_unmute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("全体解禁", Args["status?", bool, False]),
    aliases={
        "全员解禁",
        "关闭全体禁言",
        "解除全体禁言",
        "全解禁",
        "全体解禁",
        "关闭全员禁言",
        "解除全员禁言",
        "解禁群",
    },
    priority=5,
    block=True,
)


@member_mute_cmd.handle()
async def milkybot_mute(
    user: At,
    duration: int,
    reason: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    await bot.set_group_member_mute(
        group_id=event.data.peer_id, user_id=user.data["user_id"], duration=duration
    )
    msg: UniMessage[Text] = UniMessage(
        message=f"已禁言 {user.data['user_id']}，时长 {duration} 秒，原因：{reason}"
    )
    logger.info(msg)
    await member_mute_cmd.finish(message=msg)


@whole_mute_cmd.handle()
async def milkybot_whole_mute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    *,
    status: bool = True,
) -> Any:
    if status:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=status)
    msg: UniMessage[Text] = UniMessage(message="全体禁言成功")
    logger.info(msg)
    await whole_mute_cmd.finish(message=msg)


@member_unmute_cmd.handle()
async def milkybot_unmute(
    user: At,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    await bot.set_group_member_mute(
        group_id=event.data.peer_id, user_id=user.data["user_id"], duration=0
    )
    msg: UniMessage[Text] = UniMessage(message=f"已解禁用户 {user.data['user_id']}")
    logger.info(msg)
    await member_unmute_cmd.finish(message=msg)


@whole_unmute_cmd.handle()
async def milkybot_whole_unmute(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    *,
    status: bool = False,
) -> Any:
    if not status:
        await bot.set_group_whole_mute(group_id=event.data.peer_id, is_mute=status)
    msg: UniMessage[Text] = UniMessage(message="全体解禁成功")
    logger.info(msg)
    await whole_unmute_cmd.finish(message=msg)


async def import_handle() -> None:
    logger.debug("导入处理器...")
