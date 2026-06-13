from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import Event as OneBot11Event
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

from ......services.permissions import (
    PermissionContext,
    visible_command_keys,
)
from .....menu import (
    ONEBOT_V11_ADAPTER_ID,
    menu_cmd,
    menu_page_cmds,
    qq_menu_context,
    render_menu_index,
    render_menu_page,
)
from ....group.common import selected_adapter_handle

onebot11_menu_pages: dict[str, Any] = {}


@selected_adapter_handle(menu_cmd, "~onebot.v11")
async def onebot11_menu(
    bot: OneBot11Bot,
    event: OneBot11Event | None = None,
) -> Any:
    context = await _onebot11_menu_context(bot)
    allowed = await _visible_commands(bot, context, event)
    return await menu_cmd.finish(
        message=render_menu_index(context, allowed_command_keys=allowed)
    )


def _register_onebot11_menu_page(page_id: str) -> None:
    command = menu_page_cmds[page_id]

    @selected_adapter_handle(command, "~onebot.v11")
    async def onebot11_menu_page(
        bot: OneBot11Bot,
        event: OneBot11Event | None = None,
    ) -> Any:
        context = await _onebot11_menu_context(bot)
        allowed = await _visible_commands(bot, context, event)
        return await command.finish(
            message=render_menu_page(page_id, context, allowed_command_keys=allowed)
        )

    onebot11_menu_pages[page_id] = onebot11_menu_page


for _page_id in menu_page_cmds:
    _register_onebot11_menu_page(_page_id)


async def _onebot11_menu_context(bot: OneBot11Bot) -> Any:
    try:
        version_info = await bot.get_version_info()
    except (OneBot11ActionFailed, RuntimeError, TypeError, ValueError) as error:
        data: dict[str, Any] = {}
        logger.debug(f"Lingchu 获取 OneBot 实现信息失败: {error!r}")
    else:
        data = version_info.get("data", version_info)

    return qq_menu_context(
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        implementation_name=_string_or_none(data.get("app_name")),
        implementation_version=_string_or_none(data.get("app_version")),
        protocol_version=_string_or_none(data.get("protocol_version")),
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


async def _visible_commands(
    bot: OneBot11Bot,
    context: Any,
    event: OneBot11Event | None,
) -> frozenset[str] | None:
    if event is None:
        return None
    permission_context = PermissionContext(
        platform_id=context.platform_id,
        adapter_id=context.adapter_id,
        implementation_name=context.implementation_name,
        command_key="menu",
        user_id=_event_user_id(event),
        bot_id=_string_or_none(getattr(bot, "self_id", None)),
        resource_type="group" if getattr(event, "group_id", None) is not None else None,
        resource_id=_string_or_none(getattr(event, "group_id", None)),
        native_roles=_event_native_roles(event),
    )
    return await visible_command_keys(permission_context)


def _event_user_id(event: OneBot11Event) -> str | None:
    try:
        return str(event.get_user_id())
    except Exception:  # noqa: BLE001
        return _string_or_none(getattr(event, "user_id", None))


def _event_native_roles(event: OneBot11Event) -> frozenset[str]:
    sender = getattr(event, "sender", None)
    role = getattr(sender, "role", None)
    return _normalize_native_role(role)


def _normalize_native_role(role: Any) -> frozenset[str]:
    normalized = str(role).casefold() if role is not None else ""
    if normalized in {"owner", "admin", "administrator"}:
        return frozenset({"admin" if normalized == "administrator" else normalized})
    if normalized in {"member", ""}:
        return frozenset()
    return frozenset({normalized})


async def import_handle() -> Any:
    return None
