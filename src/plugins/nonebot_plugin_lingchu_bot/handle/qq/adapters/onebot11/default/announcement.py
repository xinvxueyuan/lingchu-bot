from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBBot11_GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import Image as UniImage
from packaging.version import InvalidVersion, parse

from ......core.runtime_config import get_handle_config_manager
from ......i18n import _async as _
from ....commands.announcement import (
    AnnouncementImagePath,
    _resolve_image_path,
    send_group_announcement_cmd,
)
from ....commands.common import selected_adapter_handle
from ..napcat.announcement import send_group_notice_napcat
from .common import check_bot_privilege


async def _resolve_announcement_action(bot: OneBot11) -> tuple[Any | None, str | None]:
    version_info = await bot.get_version_info()
    # OneBot V11 适配器解包响应，get_version_info() 直接返回 data 字段
    data = version_info.get("data", version_info)

    if data.get("protocol_version") != "v11":
        return None, await _("不支持的 OneBot 协议版本")

    raw_version = data.get("app_version", "0")
    try:
        current_version = parse(raw_version)
    except InvalidVersion:
        current_version = parse("0")

    app_name = data.get("app_name")
    match app_name:
        case "NapCat.Onebot" if current_version >= parse("4.18.0"):
            return send_group_notice_napcat, None
        case _:
            return None, await _("不支持的 OneBot 版本")


async def send_onebot11_group_announcement_notice(
    *,
    bot: OneBot11,
    event: OneBBot11_GroupMessageEvent,
    group_id: int,
    content: str,
    image_path: AnnouncementImagePath | None,
) -> str | None:
    action, error_msg = await _resolve_announcement_action(bot)
    if error_msg is not None:
        return error_msg
    if action is None:
        return await _("不支持的 OneBot 版本")

    await action(
        content=content,
        group_id=group_id,
        image_path=image_path,
        bot=bot,
        event=event,
    )
    return None


@selected_adapter_handle(
    send_group_announcement_cmd,
    "~onebot.v11",
    "send_announcement",
)
async def onebot_v11_send_group_announcement(
    content: str,
    image: UniImage | None,
    bot: OneBot11,
    event: OneBBot11_GroupMessageEvent,
) -> None:
    # 检查功能是否启用
    config = get_handle_config_manager().get_config("send_announcement")
    if not config.enabled:
        await send_group_announcement_cmd.finish(await _("该功能已禁用"))
        return

    # 1. 输入数据清洗：去除首尾空白字符
    content = content.strip()

    # 2. 参数合法性检查
    if not content:
        await send_group_announcement_cmd.finish(await _("群公告内容不能为空"))
        return

    # 3. 解析图片路径
    image_path = await _resolve_image_path(image) if image is not None else None

    # 4. 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, send_group_announcement_cmd):
        return

    try:
        error_msg = await send_onebot11_group_announcement_notice(
            bot=bot,
            event=event,
            group_id=event.group_id,
            content=content,
            image_path=image_path,
        )
        if error_msg is not None:
            await send_group_announcement_cmd.finish(error_msg)
            return
    except OneBot11ActionFailed as e:
        logger.error(f"发送群公告失败，操作被拒绝: {e!r}")
        await send_group_announcement_cmd.finish(await _("发送群公告失败，操作被拒绝"))
        return

    # 7. 反馈结果
    await send_group_announcement_cmd.finish(await _("群公告已发送"))
