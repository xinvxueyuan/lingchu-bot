from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ......i18n import _async as _
from ....commands.announcement import _resolve_image_path, send_group_announcement_cmd
from ....commands.common import selected_adapter_handle
from ..llbot.announcement import send_group_announcement_llbot


@selected_adapter_handle(send_group_announcement_cmd, "~milky")
async def milkybot_send_group_announcement(
    content: str,
    image: UniImage | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> None:
    # 1. 输入数据清洗：去除首尾空白字符
    content = content.strip()

    # 2. 参数合法性检查
    if not content:
        await send_group_announcement_cmd.finish(await _("群公告内容不能为空"))
        return

    # 3. 解析图片路径
    image_path = await _resolve_image_path(image) if image is not None else None

    # 4. 获取实现信息
    try:
        impl_info = await bot.get_impl_info()
    except (NetworkError, ActionFailed) as e:
        logger.error(f"获取实现信息失败: {e!r}")
        await send_group_announcement_cmd.finish(await _("获取实现信息失败"))
        return

    # 5. 选择对应的实现
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

    # 6. 执行发送操作
    try:
        await send_group_announcement_llbot(
            content=content,
            image_path=image_path,
            bot=bot,
            event=event,
        )
    except NetworkError as e:
        logger.error(f"发送群公告失败，网络异常: {e!r}")
        await send_group_announcement_cmd.finish(await _("发送群公告失败，网络异常"))
        return
    except ActionFailed as e:
        logger.error(f"发送群公告失败，操作被拒绝: {e!r}")
        await send_group_announcement_cmd.finish(await _("发送群公告失败，操作被拒绝"))
        return

    # 7. 反馈结果
    await send_group_announcement_cmd.finish(await _("群公告已发送"))
