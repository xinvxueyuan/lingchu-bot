from typing import Any

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

from ......core.runtime_config import get_handle_config_manager
from ......database.orm_crud import DatabaseError
from ......i18n import _async as _
from ......permissions.subject_policy import (
    SubjectPolicyUpsert,
    remove_subject_policy,
    upsert_subject_policy,
)
from ......repositories.blocklist import BlockScope
from ....commands.common import selected_adapter_handle
from ....commands.protect import (
    global_protect_member_cmd,
    global_unprotect_member_cmd,
    protect_member_cmd,
    unprotect_member_cmd,
)
from .common import (
    ONEBOT_V11_ADAPTER_ID,
    QQ_PLATFORM_ID,
    CommandAudit,
    bot_id,
    default_admin_reason,
    format_user_display_name,
    operator_is_superuser_onebot11,
    record_audit_fire_and_forget,
    resolve_user_onebot11,
)


async def _finish_database_error(
    command: Any, operation: str, error: DatabaseError
) -> Any:
    logger.error(f"{operation}失败，数据库异常: {error!r}")
    return await command.finish(
        message=(await _("{operation}失败，数据库异常: {error!r}")).format(
            operation=operation,
            error=error,
        )
    )


async def _require_superuser(command: Any, event: OneBot11GroupMessageEvent) -> bool:
    if await operator_is_superuser_onebot11(event.user_id):
        return True
    await command.finish(await _("权限不足"))
    return False


async def _protect_member(
    *,
    command: Any,
    scope: BlockScope,
    user: At | int,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    if not await _require_superuser(command, event):
        return None
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)
    reason_text = await default_admin_reason(reason)
    try:
        await upsert_subject_policy(
            SubjectPolicyUpsert(
                policy_type="protected",
                platform_id=QQ_PLATFORM_ID,
                adapter_id=ONEBOT_V11_ADAPTER_ID,
                bot_id=bot_id(bot),
                scope=scope,
                group_id=event.group_id,
                user_id=target_user_id,
                operator_id=event.user_id,
                reason=reason_text,
                expires_at=None,
            )
        )
    except DatabaseError as error:
        return await _finish_database_error(command, await _("拉白"), error)

    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="protect_member",
            target_user_id=target_user_id,
            reason=reason_text,
        ),
    )

    scope_text = await _("全局") if scope == "global" else await _("本群")
    name_display = format_user_display_name(target_user_id, target_name)
    message = (
        await _(
            "已拉白: \n"
            "范围: {scope}\n"
            "名称: {name_display}\n"
            "原因: {reason}\n"
            "标识: {target_user_id}"
        )
    ).format(
        scope=scope_text,
        name_display=name_display,
        reason=reason_text,
        target_user_id=target_user_id,
    )
    logger.info(message)
    return await command.finish(message=message)


@selected_adapter_handle(protect_member_cmd, "~onebot.v11", "protect_member")
async def onebot11_protect_member(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("protect_member")
    if not config.enabled:
        return await protect_member_cmd.finish(await _("该功能已禁用"))

    # 读取配置中的默认scope
    whitelist_scope = config.defaults.get("whitelist_scope", "group")

    return await _protect_member(
        command=protect_member_cmd,
        scope=whitelist_scope,
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )


@selected_adapter_handle(
    global_protect_member_cmd,
    "~onebot.v11",
    "global_protect_member",
)
async def onebot11_global_protect_member(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 检查功能是否启用（global版本共用protect_member配置）
    config = await get_handle_config_manager().get_config("protect_member")
    if not config.enabled:
        return await global_protect_member_cmd.finish(await _("该功能已禁用"))

    return await _protect_member(
        command=global_protect_member_cmd,
        scope="global",
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )


async def _unprotect_member(
    *,
    command: Any,
    scope: BlockScope,
    user: At | int,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    if not await _require_superuser(command, event):
        return None
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)
    reason_text = await default_admin_reason(reason)
    try:
        result = await remove_subject_policy(
            policy_type="protected",
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=bot_id(bot),
            scope=scope,
            group_id=event.group_id,
            user_id=target_user_id,
        )
        deleted = result[0]
    except DatabaseError as error:
        return await _finish_database_error(command, await _("删白"), error)

    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="unprotect_member",
            target_user_id=target_user_id,
            reason=reason_text,
        ),
    )

    scope_text = await _("全局") if scope == "global" else await _("本群")
    name_display = format_user_display_name(target_user_id, target_name)
    message = (
        await _(
            "已删白: \n"
            "范围: {scope}\n"
            "名称: {name_display}\n"
            "原因: {reason}\n"
            "标识: {target_user_id}\n"
            "删除记录: {deleted}"
        )
    ).format(
        scope=scope_text,
        name_display=name_display,
        reason=reason_text,
        target_user_id=target_user_id,
        deleted=deleted,
    )
    logger.info(message)
    return await command.finish(message=message)


@selected_adapter_handle(unprotect_member_cmd, "~onebot.v11", "unprotect_member")
async def onebot11_unprotect_member(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 检查功能是否启用（取消保护共用protect_member配置）
    config = await get_handle_config_manager().get_config("protect_member")
    if not config.enabled:
        return await unprotect_member_cmd.finish(await _("该功能已禁用"))

    return await _unprotect_member(
        command=unprotect_member_cmd,
        scope="group",
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )


@selected_adapter_handle(
    global_unprotect_member_cmd,
    "~onebot.v11",
    "global_unprotect_member",
)
async def onebot11_global_unprotect_member(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    # 检查功能是否启用（取消保护共用protect_member配置）
    config = await get_handle_config_manager().get_config("protect_member")
    if not config.enabled:
        return await global_unprotect_member_cmd.finish(await _("该功能已禁用"))

    return await _unprotect_member(
        command=global_unprotect_member_cmd,
        scope="global",
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )
