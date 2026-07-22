"""Smoke test verifying all runtime hooks are registered with NoneBot."""

from __future__ import annotations

from typing import Any

import nonebot
from nonebot.adapters import Bot
from nonebot.message import (
    _event_postprocessors,
    _event_preprocessors,
    _run_postprocessors,
    _run_preprocessors,
)


def _dependent_calls(registry: Any) -> set[Any]:
    """Return the underlying callable for each NoneBot hook registry entry."""
    calls: set[Any] = set()
    for entry in registry:
        call = getattr(entry, "call", entry)
        calls.add(call)
    return calls


async def check_hook_registration() -> None:
    """Verify lifecycle, bot_connection, message_store and api_audit hooks.

    Importing hooks.handlers triggers the parent hooks/__init__.py, which
    registers all runtime hooks with NoneBot as a side effect.
    """
    from nonebot_plugin_lingchu_bot.hooks.handlers import (
        api_audit,
        bot_connection,
        lifecycle,
        message_store,
    )

    driver = nonebot.get_driver()

    event_pre_calls = _dependent_calls(_event_preprocessors)
    event_post_calls = _dependent_calls(_event_postprocessors)
    run_pre_calls = _dependent_calls(_run_preprocessors)
    run_post_calls = _dependent_calls(_run_postprocessors)

    assert message_store.message_store_preprocessor in event_pre_calls
    assert message_store.message_store_postprocessor in event_post_calls
    assert message_store.message_store_run_preprocessor in run_pre_calls
    assert message_store.message_store_run_postprocessor in run_post_calls

    assert api_audit.on_calling_api in Bot._calling_api_hook
    assert api_audit.on_called_api in Bot._called_api_hook

    assert lifecycle.on_startup in driver._lifespan._startup_funcs
    assert lifecycle.on_shutdown in driver._lifespan._shutdown_funcs

    bot_connect_calls = _dependent_calls(driver._bot_connection_hook)
    bot_disconnect_calls = _dependent_calls(driver._bot_disconnection_hook)
    assert bot_connection.on_bot_connect in bot_connect_calls
    assert bot_connection.on_bot_disconnect in bot_disconnect_calls


async def test_hook_registration() -> None:
    """Pytest entry point for ``check_hook_registration``."""
    await check_hook_registration()
