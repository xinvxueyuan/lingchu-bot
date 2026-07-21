from typing import Any

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import Image as UniImage

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session
from packaging.version import InvalidVersion, parse

from ......core.config import get_handle_config_manager
from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.profile import (
    _resolve_image_path,
    set_group_avatar_cmd,
    set_group_name_cmd,
)
from ..napcat.profile import set_group_portrait_napcat

# 群名称长度限制
_GROUP_NAME_MAX_LENGTH = 50


@selected_adapter_handle(set_group_name_cmd, "~onebot.v11", "set_group_name")
async def onebot11_set_group_name(
    new_group_name: str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("set_group_name")
    if not config.enabled:
        return await set_group_name_cmd.finish(await _("该功能已禁用"))

    # 1. 输入数据清洗：去除首尾空白字符
    new_group_name = new_group_name.strip()

    # 2. 参数合法性检查
    if not new_group_name:
        return await set_group_name_cmd.finish(await _("群名称不能为空"))

    if len(new_group_name) > _GROUP_NAME_MAX_LENGTH:
        return await set_group_name_cmd.finish(
            (await _("群名称长度不能超过 {max} 个字符")).format(
                max=_GROUP_NAME_MAX_LENGTH
            )
        )

    # 3. 执行设置群名称操作
    try:
        await bot.set_group_name(group_id=event.group_id, group_name=new_group_name)
    except OneBot11ActionFailed as e:
        logger.error(f"设置群名称失败，操作被拒绝: {e!r}")
        return await set_group_name_cmd.finish(await _("设置群名称失败，操作被拒绝"))

    # 4. 格式化反馈消息
    message = await _("群名称已设置为: {new_group_name}")
    return await set_group_name_cmd.finish(
        message.format(new_group_name=new_group_name)
    )


@selected_adapter_handle(set_group_avatar_cmd, "~onebot.v11", "set_group_avatar")
async def onebot11_set_group_avatar(
    image: UniImage | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("set_group_avatar")
    if not config.enabled:
        return await set_group_avatar_cmd.finish(await _("该功能已禁用"))

    # 1. 解析图片路径
    image_path = await _resolve_image_path(image)
    if image_path is None:
        return await set_group_avatar_cmd.finish(await _("请上传一张图片"))

    # 2. 获取版本信息
    try:
        version_info = await bot.get_version_info()
        # OneBot V11 适配器解包响应，get_version_info() 直接返回 data 字段
        data = version_info.get("data", version_info)
        app_name = data.get("app_name")
        raw_version = data.get("app_version", "0")
        try:
            current_version = parse(raw_version)
        except InvalidVersion:
            current_version = parse("0")

        # 3. 选择对应的实现
        match app_name:
            case "NapCat.Onebot" if current_version >= parse("4.18.0"):

                async def _set_portrait() -> None:
                    await set_group_portrait_napcat(
                        image_path=image_path, bot=bot, event=event
                    )

                action = _set_portrait
            case _:
                return await set_group_avatar_cmd.finish(
                    await _("当前 OneBot 实现不支持设置群头像")
                )

        # 4. 执行设置头像操作
        await action()
    except OneBot11ActionFailed as e:
        logger.error(f"设置群头像失败，操作被拒绝: {e!r}")
        return await set_group_avatar_cmd.finish(await _("设置群头像失败，操作被拒绝"))

    # 5. 反馈结果
    return await set_group_avatar_cmd.finish(await _("群头像已更新"))
