from typing import Any

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

from ......core.runtime_config import get_handle_config_manager
from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.kick import kick_member_cmd
from .common import (
    CommandAudit,
    check_bot_privilege,
    check_self_target,
    check_target_privilege,
    format_user_display_name,
    record_audit_fire_and_forget,
    resolve_user_onebot11,
)


async def _kick_member(
    *,
    command: type[Any],
    user: At | int,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    """踢出群成员核心逻辑"""
    # 解析用户
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)

    # 边界条件检查
    if not await check_self_target(target_user_id, bot, event, command, "踢出"):
        return None

    if not await check_target_privilege(bot, event, target_user_id, command):
        return None

    # 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, command):
        return None

    # 执行踢出操作
    try:
        await bot.set_group_kick(
            group_id=event.group_id,
            user_id=target_user_id,
            reject_add_request=False,
        )
    except OneBot11ActionFailed as e:
        logger.error(f"踢出群成员失败: {e!r}")
        return await command.finish(await _("踢出群成员失败，操作被拒绝"))

    # 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="kick_member",
            target_user_id=target_user_id,
            reason=reason,
        ),
    )

    # 反馈结果
    display_name = format_user_display_name(target_user_id, target_name)
    reason_text = f"，原因: {reason}" if reason else ""
    message = await _("已踢出群成员 {name}{reason}")
    return await command.finish(message.format(name=display_name, reason=reason_text))


@selected_adapter_handle(kick_member_cmd, "~onebot.v11", "kick_member")
async def onebot11_kick_member(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    """OneBot V11 踢出群成员处理器"""
    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("kick_member")
    if not config.enabled:
        return await kick_member_cmd.finish(await _("该功能已禁用"))

    if config.defaults.get("require_reason", False) and not reason:
        return await kick_member_cmd.finish(await _("踢出群成员时必须提供原因"))

    return await _kick_member(
        command=kick_member_cmd,
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )
