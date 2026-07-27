"""Telegram menu handlers.

Note: do NOT add `from __future__ import annotations` here. NoneBot resolves
handler signature forward refs via the wrapper's __globals__ (common.py), which
cannot see Telegram event types. Use real type objects like the OneBot V11 siblings.
"""

from typing import Any

from nonebot import require
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import Event

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from .....permissions import allowed_command_keys
from ....menu import (
    MENU_FEATURES,
    menu_cmd,
    menu_page_cmds,
    render_menu_index,
    render_menu_page,
    telegram_menu_context,
)
from ....qq.commands.common import selected_adapter_handle

telegram_menu_pages: dict[str, Any] = {}


async def _allowed_menu_keys(
    session: async_scoped_session,
    bot: Bot,
    event: Event | None,
) -> frozenset[str] | None:
    if event is None:
        return None
    command_keys = frozenset(feature.command_key for feature in MENU_FEATURES)
    return await allowed_command_keys(session, bot, event, command_keys)


@selected_adapter_handle(menu_cmd, "~telegram")
async def telegram_menu(
    bot: Bot,
    session: async_scoped_session,
    _event: Event | None = None,
) -> Any:
    allowed = await _allowed_menu_keys(session, bot, _event)
    return await menu_cmd.finish(
        message=render_menu_index(
            telegram_menu_context(),
            allowed_command_keys=allowed,
        )
    )


def _register_menu_page(page_id: str) -> None:
    command = menu_page_cmds[page_id]

    @selected_adapter_handle(command, "~telegram")
    async def telegram_menu_page(
        bot: Bot,
        session: async_scoped_session,
        _event: Event | None = None,
    ) -> Any:
        allowed = await _allowed_menu_keys(session, bot, _event)
        return await command.finish(
            message=render_menu_page(
                page_id,
                telegram_menu_context(),
                allowed_command_keys=allowed,
            )
        )

    telegram_menu_pages[page_id] = telegram_menu_page


for _page_id in menu_page_cmds:
    _register_menu_page(_page_id)


async def import_handle() -> None:
    """Register Telegram menu handlers."""
