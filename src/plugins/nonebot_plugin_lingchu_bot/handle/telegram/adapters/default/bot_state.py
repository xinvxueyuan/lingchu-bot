"""Telegram bot state handlers.

Note: do NOT add `from __future__ import annotations` here. NoneBot resolves
handler signature forward refs via the wrapper's __globals__ (common.py), which
cannot see GroupMessageEvent. Use real type objects like the OneBot V11 siblings.
"""

from typing import Any

from nonebot import require
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import GroupMessageEvent

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from .....core.bot_state import set_global_handle_active, set_global_silent_mode
from .....i18n import _async as _
from ....qq.commands.bot_state import (
    bot_boot_cmd,
    bot_shutdown_cmd,
    bot_silence_cmd,
    bot_speak_cmd,
)
from ....qq.commands.common import selected_adapter_handle


@selected_adapter_handle(
    bot_silence_cmd,
    "~telegram",
    "bot_silence",
    bypass_silent=True,
)
async def telegram_bot_silence(
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del bot, event, session
    set_global_silent_mode(silent=True)
    return await bot_silence_cmd.finish(await _("已进入静默模式"))


@selected_adapter_handle(
    bot_speak_cmd,
    "~telegram",
    "bot_speak",
    bypass_silent=True,
)
async def telegram_bot_speak(
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del bot, event, session
    set_global_silent_mode(silent=False)
    return await bot_speak_cmd.finish(await _("已退出静默模式"))


@selected_adapter_handle(
    bot_boot_cmd,
    "~telegram",
    "bot_boot",
    bypass_gate=True,
    bypass_silent=True,
)
async def telegram_bot_boot(
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del bot, event, session
    set_global_handle_active(active=True)
    return await bot_boot_cmd.finish(await _("已开机"))


@selected_adapter_handle(
    bot_shutdown_cmd,
    "~telegram",
    "bot_shutdown",
    bypass_gate=True,
    bypass_silent=True,
)
async def telegram_bot_shutdown(
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del bot, event, session
    set_global_handle_active(active=False)
    return await bot_shutdown_cmd.finish(await _("已关机"))
