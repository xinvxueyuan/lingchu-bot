"""OneBot V11 handlers for runtime handle-default management."""

from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

from ......core.handle_default_values import (
    HandleDefaultValueError,
    supported_handle_defaults,
    update_handle_default,
)
from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.handle_defaults import manage_handle_defaults_cmd
from .common import CommandAudit, record_audit_fire_and_forget


@selected_adapter_handle(
    manage_handle_defaults_cmd, "~onebot.v11", "manage_handle_defaults"
)
async def onebot11_manage_handle_defaults(
    handle: str | None,
    field: str | None,
    value: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    """List supported defaults or update one typed default field."""
    if handle is None:
        fields = ", ".join(
            f"{item.command_key}.{item.field}" for item in supported_handle_defaults()
        )
        return await manage_handle_defaults_cmd.finish(
            (await _("可修改的功能默认值: {fields}")).format(fields=fields)
        )
    if field is None or value is None:
        return await manage_handle_defaults_cmd.finish(
            await _("用法: 设置功能默认值 <功能> <字段> <值>")
        )
    try:
        updated = await update_handle_default(handle, field, value)
    except HandleDefaultValueError:
        return await manage_handle_defaults_cmd.finish(await _("功能默认值或值无效"))
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="manage_handle_defaults",
            reason=f"{handle}.{field}={updated}",
        ),
    )
    return await manage_handle_defaults_cmd.finish(
        (await _("已更新功能默认值: {handle}.{field} = {value}")).format(
            handle=handle, field=field, value=updated
        )
    )
