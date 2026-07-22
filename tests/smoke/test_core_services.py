"""Smoke test verifying core Lingchu services can be initialized."""

from __future__ import annotations


async def check_core_services() -> None:
    """Verify bot_state, message_store and scheduler services initialize.

    These functions are intentionally isolated from real protocol adapters and
    only assert that the service-layer initialization paths execute without
    raising.
    """
    from nonebot_plugin_lingchu_bot.core.bot_state import load_bot_state
    from nonebot_plugin_lingchu_bot.services.message_store import (
        initialize_message_store,
    )
    from nonebot_plugin_lingchu_bot.services.scheduler import (
        initialize_scheduler_service,
    )

    await load_bot_state()
    await initialize_message_store()
    await initialize_scheduler_service()


async def test_core_services() -> None:
    """Pytest entry point for ``check_core_services``."""
    await check_core_services()
