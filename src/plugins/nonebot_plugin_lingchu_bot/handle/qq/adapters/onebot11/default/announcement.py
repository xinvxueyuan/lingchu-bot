from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBBot11_GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import Image as UniImage
from packaging.version import InvalidVersion, parse

from ......i18n import _async as _
from ....commands.announcement import _resolve_image_path, send_group_announcement_cmd
from ....commands.common import selected_adapter_handle
from ..llonebot.announcement import send_group_notice_llonebot
from ..napcat.announcement import send_group_notice_napcat


@selected_adapter_handle(send_group_announcement_cmd, "~onebot.v11")
async def onebot_v11_send_group_announcement(
    content: str,
    image: UniImage | None,
    bot: OneBot11,
    event: OneBBot11_GroupMessageEvent,
) -> None:
    # 1. 输入数据清洗：去除首尾空白字符
    content = content.strip()

    # 2. 参数合法性检查
    if not content:
        await send_group_announcement_cmd.finish(await _("群公告内容不能为空"))
        return

    # 3. 解析图片路径
    image_path = await _resolve_image_path(image) if image is not None else None

    # 4. 获取版本信息
    try:
        version_info = await bot.get_version_info()
        # OneBot V11 适配器解包响应，get_version_info() 直接返回 data 字段
        data = version_info.get("data", version_info)

        if data.get("protocol_version") != "v11":
            await send_group_announcement_cmd.finish(
                await _("不支持的 OneBot 协议版本")
            )
            return

        raw_version = data.get("app_version", "0")
        try:
            current_version = parse(raw_version)
        except InvalidVersion:
            current_version = parse("0")

        app_name = data.get("app_name")

        # 5. 选择对应的实现
        match app_name:
            case "LLOneBot" if current_version >= parse("7.12.0"):
                action = send_group_notice_llonebot
            case "NapCat.Onebot" if current_version >= parse("4.18.0"):
                action = send_group_notice_napcat
            case _:
                await send_group_announcement_cmd.finish(
                    await _("不支持的 OneBot 版本")
                )
                return

        # 6. 执行发送操作
        await action(
            content=content,
            image_path=image_path,
            bot=bot,
            event=event,
        )
    except OneBot11ActionFailed as e:
        logger.error(f"发送群公告失败，操作被拒绝: {e!r}")
        await send_group_announcement_cmd.finish(await _("发送群公告失败，操作被拒绝"))
        return

    # 7. 反馈结果
    await send_group_announcement_cmd.finish(await _("群公告已发送"))
