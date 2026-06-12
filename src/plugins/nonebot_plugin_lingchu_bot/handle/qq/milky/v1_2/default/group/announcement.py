from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna.uniseg import Image as UniImage

from .......i18n import _async as _
from .....group.announcement import _resolve_image_path, send_group_announcement_cmd
from .....group.common import selected_adapter_handle
from ...llbot.group.announcement import send_group_announcement_llbot
from .common import run_group_action_milky


@selected_adapter_handle(send_group_announcement_cmd, "~milky")
async def milkybot_send_group_announcement(
    content: str,
    image: UniImage | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> None:
    image_path = await _resolve_image_path(image) if image is not None else None
    impl_info = await bot.get_impl_info()

    match impl_info.impl_name:
        case "LLBot":
            if image is not None:
                await send_group_announcement_cmd.finish(
                    await _("协议端功能异常，等待上游修复")
                )
                return
        case _:
            await send_group_announcement_cmd.finish(await _("不支持的 Milky 实现"))
            return

    await run_group_action_milky(
        send_group_announcement_cmd,
        await _("发送群公告"),
        lambda: send_group_announcement_llbot(
            content=content,
            image_path=image_path,
            bot=bot,
            event=event,
        ),
        await _("群公告已发送"),
    )
