from typing import Any

from arclet.alconna import Alconna, Args
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from ....i18n import _async as _
from .common import run_group_action

set_group_name_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群名称", Args["new_group_name", str]),
    aliases={"改群名", "修改群名称", "设置群名"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_avatar_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群头像", Args["image_uri", str]),
    aliases={"改群头像", "修改群头像"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


async def _set_group_avatar(
    bot: MilkyBot,
    group_id: int,
    image_uri: str,
) -> None:
    if image_uri.startswith("file://"):
        await bot.set_group_avatar(
            group_id=group_id, path=image_uri.removeprefix("file://")
        )
    elif image_uri.startswith("base64://"):
        await bot.set_group_avatar(
            group_id=group_id, base64=image_uri.removeprefix("base64://")
        )
    else:
        await bot.set_group_avatar(group_id=group_id, url=image_uri)


@set_group_name_cmd.handle()
async def milkybot_set_group_name(
    new_group_name: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    return await run_group_action(
        set_group_name_cmd,
        await _("设置群名称"),
        lambda: bot.set_group_name(
            group_id=event.data.peer_id, new_group_name=new_group_name
        ),
        (await _("群名称已设置为: {new_group_name}")).format(
            new_group_name=new_group_name
        ),
    )


@set_group_avatar_cmd.handle()
async def milkybot_set_group_avatar(
    image_uri: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    return await run_group_action(
        set_group_avatar_cmd,
        await _("设置群头像"),
        lambda: _set_group_avatar(bot, event.data.peer_id, image_uri),
        await _("群头像已更新"),
    )
