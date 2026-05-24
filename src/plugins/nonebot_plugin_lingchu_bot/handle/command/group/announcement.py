from typing import Any

from arclet.alconna import Alconna, Args
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from ....i18n import _async as _
from .common import run_group_action

send_group_announcement_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("发送群公告", Args["content", str]["image_uri?", str, None]),
    aliases={"发群公告", "群公告"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


async def _send_group_announcement(
    bot: MilkyBot,
    group_id: int,
    content: str,
    image_uri: str | None,
) -> None:
    if image_uri is None:
        await bot.send_group_announcement(group_id=group_id, content=content)
    elif image_uri.startswith("file://"):
        await bot.send_group_announcement(
            group_id=group_id,
            content=content,
            path=image_uri.removeprefix("file://"),
        )
    elif image_uri.startswith("base64://"):
        await bot.send_group_announcement(
            group_id=group_id,
            content=content,
            base64=image_uri.removeprefix("base64://"),
        )
    else:
        await bot.send_group_announcement(
            group_id=group_id,
            content=content,
            url=image_uri,
        )


@send_group_announcement_cmd.handle()
async def milkybot_send_group_announcement(
    content: str,
    image_uri: str | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    return await run_group_action(
        send_group_announcement_cmd,
        await _("发送群公告"),
        lambda: _send_group_announcement(bot, event.data.peer_id, content, image_uri),
        await _("群公告已发送"),
    )
