from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import At

from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.member import (
    kick_group_member_cmd,
    set_group_member_admin_cmd,
    set_group_member_card_cmd,
    set_group_member_special_title_cmd,
    unset_group_member_admin_cmd,
)
from .common import (
    bot_self_id_safe,
    check_bot_privilege,
    check_target_privilege,
    record_command_audit,
    resolve_user_onebot11,
)

# 群名片长度限制
_CARD_MAX_LENGTH = 60
# 群头衔长度限制
_TITLE_MAX_LENGTH = 60


@selected_adapter_handle(set_group_member_card_cmd, "~onebot.v11", "set_member_card")
async def onebot11_set_group_member_card(
    user: At | int,
    card: str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 1. 输入数据清洗：去除首尾空白字符
    card = card.strip()

    # 2. 参数合法性检查
    if len(card) > _CARD_MAX_LENGTH:
        return await set_group_member_card_cmd.finish(
            (await _("群名片长度不能超过 {max} 个字符")).format(max=_CARD_MAX_LENGTH)
        )

    # 3. 解析用户
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)

    # 4. 边界条件检查
    bot_self_id = bot_self_id_safe(bot)
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await set_group_member_card_cmd.finish(await _("不能修改机器人的群名片"))

    if not await check_target_privilege(
        bot, event, target_user_id, set_group_member_card_cmd
    ):
        return None

    # 5. 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, set_group_member_card_cmd):
        return None

    # 6. 执行设置群名片操作
    try:
        await bot.set_group_card(
            group_id=event.group_id, user_id=target_user_id, card=card
        )
    except OneBot11ActionFailed as e:
        logger.error(f"设置群名片失败，操作被拒绝: {e!r}")
        return await set_group_member_card_cmd.finish(
            await _("设置群名片失败，操作被拒绝")
        )

    # 7. 记录审计
    await record_command_audit(
        bot, event, action="set_member_card", target_user_id=target_user_id
    )

    # 8. 格式化反馈消息
    name_display = (
        f"{target_name}({target_user_id})" if target_name else str(target_user_id)
    )
    message = await _("已设置群名片: {name_display} -> {card}")
    return await set_group_member_card_cmd.finish(
        message.format(name_display=name_display, card=card)
    )


@selected_adapter_handle(
    set_group_member_special_title_cmd,
    "~onebot.v11",
    "set_member_title",
)
async def onebot11_set_group_member_special_title(
    user: At | int,
    special_title: str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 1. 输入数据清洗：去除首尾空白字符
    special_title = special_title.strip()

    # 2. 参数合法性检查
    if len(special_title) > _TITLE_MAX_LENGTH:
        return await set_group_member_special_title_cmd.finish(
            (await _("群头衔长度不能超过 {max} 个字符")).format(max=_TITLE_MAX_LENGTH)
        )

    # 3. 解析用户
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)

    # 4. 边界条件检查
    bot_self_id = bot_self_id_safe(bot)
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await set_group_member_special_title_cmd.finish(
            await _("不能修改机器人的群头衔")
        )

    if not await check_target_privilege(
        bot, event, target_user_id, set_group_member_special_title_cmd
    ):
        return None

    # 5. 机器人权限预检
    if not await check_bot_privilege(
        bot, event.group_id, set_group_member_special_title_cmd
    ):
        return None

    # 6. 执行设置群头衔操作
    try:
        await bot.set_group_special_title(
            group_id=event.group_id,
            user_id=target_user_id,
            special_title=special_title,
            duration=-1,
        )
    except OneBot11ActionFailed as e:
        logger.error(f"设置群头衔失败，操作被拒绝: {e!r}")
        return await set_group_member_special_title_cmd.finish(
            await _("设置群头衔失败，操作被拒绝")
        )

    # 7. 记录审计
    await record_command_audit(
        bot, event, action="set_member_title", target_user_id=target_user_id
    )

    # 8. 格式化反馈消息
    name_display = (
        f"{target_name}({target_user_id})" if target_name else str(target_user_id)
    )
    message = await _("已设置群头衔: {name_display} -> {special_title}")
    return await set_group_member_special_title_cmd.finish(
        message.format(name_display=name_display, special_title=special_title)
    )


@selected_adapter_handle(set_group_member_admin_cmd, "~onebot.v11", "set_member_admin")
async def onebot11_set_group_member_admin(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    *,
    is_set: bool = True,
) -> Any:
    # 1. 解析用户
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)

    # 2. 边界条件检查
    bot_self_id = bot_self_id_safe(bot)
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await set_group_member_admin_cmd.finish(
            await _("不能修改机器人的管理员权限")
        )

    # 3. 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, set_group_member_admin_cmd):
        return None

    # 4. 执行设置管理员操作
    try:
        await bot.set_group_admin(
            group_id=event.group_id, user_id=target_user_id, enable=is_set
        )
    except OneBot11ActionFailed as e:
        logger.error(f"设置管理员失败，操作被拒绝: {e!r}")
        return await set_group_member_admin_cmd.finish(
            await _("设置管理员失败，操作被拒绝")
        )

    # 5. 记录审计
    await record_command_audit(
        bot, event, action="set_member_admin", target_user_id=target_user_id
    )

    # 6. 格式化反馈消息
    action_text = await _("设置") if is_set else await _("取消")
    name_display = (
        f"{target_name}({target_user_id})" if target_name else str(target_user_id)
    )
    message = await _("{action}群管理员: {name_display}")
    return await set_group_member_admin_cmd.finish(
        message.format(action=action_text, name_display=name_display)
    )


@selected_adapter_handle(
    unset_group_member_admin_cmd,
    "~onebot.v11",
    "unset_member_admin",
)
async def onebot11_unset_group_member_admin(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    return await onebot11_set_group_member_admin(
        user=user, is_set=False, bot=bot, event=event
    )


@selected_adapter_handle(kick_group_member_cmd, "~onebot.v11", "kick_member")
async def onebot11_kick_group_member(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 1. 解析用户
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)

    # 2. 边界条件检查：不能踢自己
    if target_user_id == event.user_id:
        return await kick_group_member_cmd.finish(await _("不能踢出自己"))

    bot_self_id = bot_self_id_safe(bot)
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await kick_group_member_cmd.finish(await _("不能踢出机器人"))

    # 3. 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, kick_group_member_cmd):
        return None

    # 4. 执行踢出操作
    try:
        await bot.set_group_kick(
            group_id=event.group_id,
            user_id=target_user_id,
            reject_add_request=False,
        )
    except OneBot11ActionFailed as e:
        logger.error(f"踢出群成员失败，操作被拒绝: {e!r}")
        return await kick_group_member_cmd.finish(await _("踢出群成员失败，操作被拒绝"))

    # 5. 记录审计
    await record_command_audit(
        bot, event, action="kick_member", target_user_id=target_user_id
    )

    # 6. 格式化反馈消息
    name_display = (
        f"{target_name}({target_user_id})" if target_name else str(target_user_id)
    )
    message = await _("已踢出群成员: {name_display}")
    return await kick_group_member_cmd.finish(message.format(name_display=name_display))
