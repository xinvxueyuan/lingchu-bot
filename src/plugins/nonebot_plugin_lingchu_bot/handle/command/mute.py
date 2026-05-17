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

if TYPE_CHECKING:
    from nonebot_plugin_alconna.uniseg.segment import Text

member_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        "禁言",
        Args["user", At]["duration?", int, 60]["reason?", str, "违反群规「默认」"],
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
        Args["user", At]["reason?", str, "管理员解除禁言「默认」"],
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
    reason: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    import asyncio

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

    if event.data.sender_id != target_user_id:
        max_retries = 3
        retry_count = 0
        muted = False

        while retry_count <= max_retries:
            try:
                await bot.set_group_member_mute(
                    group_id=event.data.peer_id,
                    user_id=target_user_id,
                    duration=duration,
                )
                muted = True
                break
            except NetworkError as e:
                retry_count += 1

                if retry_count <= max_retries:
                    wait_time: Any = 2 ** (retry_count - 1)
                    logger.warning(
                        f"禁言失败 (尝试 {retry_count}/{max_retries}), "
                        f"{wait_time}秒后重试: {e}"
                    )
                    await asyncio.sleep(delay=wait_time)
                else:
                    logger.error(f"禁言失败，已重试 {max_retries} 次: {e}")
                    await member_mute_cmd.finish(
                        message=f"禁言失败，已重试{max_retries}次: {e}"
                    )
            except ActionFailed as e:
                logger.error(f"禁言失败，操作被拒绝: {e}")
                await member_mute_cmd.finish(message=f"禁言失败，操作被拒绝: {e}")

        if muted:
            msg = (
                f"已禁言: \n"
                f"名称: @{target_name}\n"
                f"时长: {duration} 秒\n"
                f"原因: {reason}\n"
                f"标识: {target_user_id}"
            )
            await member_mute_cmd.finish(message=UniMessage(message=msg))


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
        return await whole_mute_cmd.finish(message=f"全体禁言失败，网络异常: {e!r}")
    except ActionFailed as e:
        logger.error(f"全体禁言失败，操作被拒绝: {e!r}")
        return await whole_mute_cmd.finish(message=f"全体禁言失败，操作被拒绝: {e!r}")

    logger.info("全体禁言成功")
    return await whole_mute_cmd.finish(message="全体禁言成功")


@member_unmute_cmd.handle()
async def milkybot_unmute(
    user: At,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
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
    from nonebot.adapters.milky.exception import ActionFailed, NetworkError

    try:
        await bot.set_group_member_mute(
            group_id=event.data.peer_id, user_id=target_user_id, duration=0
        )
    except NetworkError as e:
        logger.error(f"解禁失败，网络异常: {e!r}")
        return await member_unmute_cmd.finish(message=f"解禁失败，网络异常: {e!r}")
    except ActionFailed as e:
        logger.error(f"解禁失败，操作被拒绝: {e!r}")
        return await member_unmute_cmd.finish(message=f"解禁失败，操作被拒绝: {e!r}")

    msg: UniMessage[Text] = UniMessage(
        message=(
            f"已解禁: \n"
            f"名称: {target_name}\n"
            f"原因: 管理员操作「默认」\n"
            f"标识: {target_user_id}"
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
        return await whole_unmute_cmd.finish(message=f"全体解禁失败，网络异常: {e!r}")
    except ActionFailed as e:
        logger.error(f"全体解禁失败，操作被拒绝: {e!r}")
        return await whole_unmute_cmd.finish(message=f"全体解禁失败，操作被拒绝: {e!r}")

    logger.info("全体解禁成功")
    return await whole_unmute_cmd.finish(message="全体解禁成功")


async def import_handle() -> Any:
    logger.debug("导入mute处理器...")
