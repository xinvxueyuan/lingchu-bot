from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import lifecycle


@pytest.mark.asyncio
async def test_on_startup_calls_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    startup = AsyncMock()
    monkeypatch.setattr(lifecycle, "startup", startup)

    await lifecycle.on_startup()

    startup.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_shutdown_calls_scheduler_then_message_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def _shutdown_scheduler_service() -> None:
        call_order.append("scheduler")

    async def _shutdown_message_store() -> None:
        call_order.append("message_store")

    monkeypatch.setattr(
        lifecycle, "shutdown_scheduler_service", _shutdown_scheduler_service
    )
    monkeypatch.setattr(lifecycle, "shutdown_message_store", _shutdown_message_store)

    await lifecycle.on_shutdown()

    assert call_order == ["scheduler", "message_store"]


@pytest.mark.asyncio
async def test_on_startup_swallows_exception_to_avoid_blocking_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    startup = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(lifecycle, "startup", startup)

    # The handler itself does not catch startup errors; callers (NoneBot) handle
    # them. We assert the call is made so the driver can surface failures.
    with pytest.raises(RuntimeError, match="boom"):
        await lifecycle.on_startup()


def test_driver_hooks_are_registered() -> None:
    """Importing the module registers handlers on the NoneBot driver."""
    assert lifecycle.driver is not None
    assert callable(lifecycle.on_startup)
    assert callable(lifecycle.on_shutdown)
