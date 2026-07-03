from __future__ import annotations

from typing import TYPE_CHECKING, Any

import nonebot
from nonebot.adapters import Bot
from nonebot.message import (
    _event_postprocessors,
    _event_preprocessors,
    _run_postprocessors,
    _run_preprocessors,
)

if TYPE_CHECKING:
    from collections.abc import Collection


def _dependent_calls(registry: Collection[Any]) -> set[Any]:
    """Return the underlying callable for each NoneBot Dependent hook entry."""
    calls: set[Any] = set()
    for entry in registry:
        call = getattr(entry, "call", entry)
        calls.add(call)
    return calls


def test_hooks_package_import_registers_all_hooks() -> None:
    """Importing the hooks package registers every runtime hook in NoneBot.

    The plugin is loaded by ``tests/conftest.py`` during NoneBot initialization,
    which executes ``from . import hooks`` in the plugin entry point. This test
    verifies that the registration side effect populated all expected NoneBot
    hook registries.
    """
    # Re-importing the hooks package is a no-op if already loaded, but it keeps
    # the test explicit about the registration trigger under verification.
    from src.plugins.nonebot_plugin_lingchu_bot import hooks  # noqa: F401
    from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import (
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
