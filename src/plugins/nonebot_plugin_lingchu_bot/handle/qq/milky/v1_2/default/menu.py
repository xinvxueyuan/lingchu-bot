from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import Event as MilkyEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from ......services.permissions import PermissionContext, visible_command_keys
from .....menu import (
    MILKY_ADAPTER_ID,
    menu_cmd,
    menu_page_cmds,
    qq_menu_context,
    render_menu_index,
    render_menu_page,
)
from ....group.common import selected_adapter_handle

milkybot_menu_pages: dict[str, Any] = {}


@selected_adapter_handle(menu_cmd, "~milky")
async def milkybot_menu(
    bot: MilkyBot,
    event: MilkyEvent | None = None,
) -> Any:
    context = await _milky_menu_context(bot)
    allowed = await _visible_commands(bot, context, event)
    return await menu_cmd.finish(
        message=render_menu_index(context, allowed_command_keys=allowed)
    )


def _register_milky_menu_page(page_id: str) -> None:
    command = menu_page_cmds[page_id]

    @selected_adapter_handle(command, "~milky")
    async def milkybot_menu_page(
        bot: MilkyBot,
        event: MilkyEvent | None = None,
    ) -> Any:
        context = await _milky_menu_context(bot)
        allowed = await _visible_commands(bot, context, event)
        return await command.finish(
            message=render_menu_page(page_id, context, allowed_command_keys=allowed)
        )

    milkybot_menu_pages[page_id] = milkybot_menu_page


for _page_id in menu_page_cmds:
    _register_milky_menu_page(_page_id)


async def _milky_menu_context(bot: MilkyBot) -> Any:
    try:
        impl_info = await bot.get_impl_info()
    except (ActionFailed, NetworkError, RuntimeError, TypeError, ValueError) as error:
        logger.debug(f"Lingchu 获取 Milky 实现信息失败: {error!r}")
        impl_name = None
        impl_version = None
    else:
        impl_name = _string_or_none(getattr(impl_info, "impl_name", None))
        impl_version = _string_or_none(getattr(impl_info, "impl_version", None))

    return qq_menu_context(
        adapter_id=MILKY_ADAPTER_ID,
        implementation_name=impl_name,
        implementation_version=impl_version,
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


async def _visible_commands(
    bot: MilkyBot,
    context: Any,
    event: MilkyEvent | None,
) -> frozenset[str] | None:
    if event is None:
        return None
    resource_id = _event_resource_id(event)
    permission_context = PermissionContext(
        platform_id=context.platform_id,
        adapter_id=context.adapter_id,
        implementation_name=context.implementation_name,
        command_key="menu",
        user_id=_event_user_id(event),
        bot_id=_string_or_none(getattr(bot, "self_id", None)),
        resource_type="group" if resource_id is not None else None,
        resource_id=resource_id,
        native_roles=_event_native_roles(event),
    )
    return await visible_command_keys(permission_context)


def _event_resource_id(event: MilkyEvent) -> str | None:
    data = getattr(event, "data", None)
    return _string_or_none(getattr(data, "peer_id", None))


def _event_user_id(event: MilkyEvent) -> str | None:
    try:
        return str(event.get_user_id())
    except Exception:  # noqa: BLE001
        data = getattr(event, "data", None)
        return _string_or_none(getattr(data, "user_id", None))


def _event_native_roles(event: MilkyEvent) -> frozenset[str]:
    data = getattr(event, "data", None)
    role = getattr(data, "sender_role", None)
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
