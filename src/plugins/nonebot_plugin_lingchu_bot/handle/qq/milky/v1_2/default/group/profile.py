from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna.uniseg import Image as UniImage

from .......i18n import _async as _
from .....group.common import selected_adapter_handle
from .....group.profile import (
    _resolve_image_path,
    set_group_avatar_cmd,
    set_group_name_cmd,
)

# 群名称长度限制
_GROUP_NAME_MAX_LENGTH = 50


@selected_adapter_handle(set_group_name_cmd, "~milky")
async def milkybot_set_group_name(
    new_group_name: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
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
        await bot.set_group_name(
            group_id=event.data.peer_id, new_group_name=new_group_name
        )
    except NetworkError as e:
        logger.error(f"设置群名称失败，网络异常: {e!r}")
        return await set_group_name_cmd.finish(await _("设置群名称失败，网络异常"))
    except ActionFailed as e:
        logger.error(f"设置群名称失败，操作被拒绝: {e!r}")
        return await set_group_name_cmd.finish(await _("设置群名称失败，操作被拒绝"))

    # 4. 格式化反馈消息
    message = await _("群名称已设置为: {new_group_name}")
    return await set_group_name_cmd.finish(
        message.format(new_group_name=new_group_name)
    )


@selected_adapter_handle(set_group_avatar_cmd, "~milky")
async def milkybot_set_group_avatar(
    image: UniImage | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    # 1. 解析图片路径
    image_path = await _resolve_image_path(image)
    if image_path is None:
        return await set_group_avatar_cmd.finish(await _("请上传一张图片"))

    # 2. 执行设置头像操作
    try:
        await bot.set_group_avatar(group_id=event.data.peer_id, path=image_path)
    except NetworkError as e:
        logger.error(f"设置群头像失败，网络异常: {e!r}")
        return await set_group_avatar_cmd.finish(await _("设置群头像失败，网络异常"))
    except ActionFailed as e:
        logger.error(f"设置群头像失败，操作被拒绝: {e!r}")
        return await set_group_avatar_cmd.finish(await _("设置群头像失败，操作被拒绝"))

    # 3. 反馈结果
    return await set_group_avatar_cmd.finish(await _("群头像已更新"))
