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
    """
    发送群公告到指定群，支持本地文件、Base64 字符串和 URL 三种图片来源。
    
    如果 image_uri 为 None 则仅发送文本内容；否则根据 image_uri 前缀选择图片参数：
    - 以 "file://" 开头时将其余部分作为本地文件路径；
    - 以 "base64://" 开头时将其余部分作为 Base64 编码内容；
    - 其他情况视为图片的 URL。
    """
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
    """
    处理“发送群公告”命令并在对应群组发送文本与可选图片公告。
    
    Parameters:
        content (str): 公告文本内容。
        image_uri (str | None): 可选图片资源定位；支持三种格式：以`file://`开头表示本地文件路径，以`base64://`开头表示图片的 Base64 编码，其余视作图片 URL。为 None 时仅发送文本公告。
        bot: 由框架提供的 MilkyBot 实例（省略常见服务的详细说明）。
        event: 群消息事件对象，用于获取目标群 ID（省略常见事件参数的详细说明）。
    
    Returns:
        Any: 发送操作的结果或状态信息，具体格式由底层实现决定。
    """
    return await run_group_action(
        send_group_announcement_cmd,
        await _("发送群公告"),
        lambda: _send_group_announcement(bot, event.data.peer_id, content, image_uri),
        await _("群公告已发送"),
    )
