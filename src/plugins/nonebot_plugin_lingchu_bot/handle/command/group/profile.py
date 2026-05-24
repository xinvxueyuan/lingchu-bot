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
    """
    根据 image_uri 的前缀选择方式并设置群头像。
    
    Parameters:
    	group_id (int): 目标群号。
    	image_uri (str): 图片资源标识。接受三种形式：
    		- 以 "file://" 开头，表示本地文件路径（使用去除前缀的路径作为文件）。
    		- 以 "base64://" 开头，表示 base64 编码的图片内容（使用去除前缀的 base64 字符串）。
    		- 其它情况视为图片 URL。
    """
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
    """
    设置群名称。
    
    Parameters:
    	new_group_name (str): 要设置的新群名称。
    
    Returns:
    	Any: 群名称设置流程返回的结果。
    """
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
    """
    设置群头像。
    
    Parameters:
    	image_uri (str): 头像资源地址，支持本地文件路径、Base64 内容或 URL。
    
    Returns:
    	Any: `run_group_action` 的返回值。
    """
    return await run_group_action(
        set_group_avatar_cmd,
        await _("设置群头像"),
        lambda: _set_group_avatar(bot, event.data.peer_id, image_uri),
        await _("群头像已更新"),
    )
