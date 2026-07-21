from typing import Any

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import Event as OneBot11Event
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from ......permissions import allowed_command_keys
from .....menu import (
    MENU_FEATURES,
    ONEBOT_V11_ADAPTER_ID,
    menu_cmd,
    menu_page_cmds,
    qq_menu_context,
    render_menu_index,
    render_menu_page,
)
from ....commands.common import selected_adapter_handle

onebot11_menu_pages: dict[str, Any] = {}


@selected_adapter_handle(menu_cmd, "~onebot.v11")
async def onebot11_menu(
    bot: OneBot11Bot,
    session: async_scoped_session,
    _event: OneBot11Event | None = None,
) -> Any:
    context = await _onebot11_menu_context(bot)
    allowed = await _allowed_menu_keys(session, bot, _event)
    return await menu_cmd.finish(
        message=render_menu_index(context, allowed_command_keys=allowed)
    )


def _register_onebot11_menu_page(page_id: str) -> None:
    command = menu_page_cmds[page_id]

    @selected_adapter_handle(command, "~onebot.v11")
    async def onebot11_menu_page(
        bot: OneBot11Bot,
        session: async_scoped_session,
        _event: OneBot11Event | None = None,
    ) -> Any:
        context = await _onebot11_menu_context(bot)
        allowed = await _allowed_menu_keys(session, bot, _event)
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


async def _allowed_menu_keys(
    session: async_scoped_session,
    bot: OneBot11Bot,
    event: OneBot11Event | None,
) -> frozenset[str] | None:
    if event is None:
        return None
    command_keys = frozenset(feature.command_key for feature in MENU_FEATURES)
    return await allowed_command_keys(session, bot, event, command_keys)


async def import_handle() -> Any:
    return None
