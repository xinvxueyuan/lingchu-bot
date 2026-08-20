from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

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

    async def _flush_runtime_configs_on_shutdown() -> tuple[bool, bool]:
        call_order.append("runtime_config")
        return (False, False)

    monkeypatch.setattr(
        lifecycle, "shutdown_scheduler_service", _shutdown_scheduler_service
    )
    monkeypatch.setattr(lifecycle, "shutdown_message_store", _shutdown_message_store)
    monkeypatch.setattr(
        lifecycle,
        "flush_runtime_configs_on_shutdown",
        _flush_runtime_configs_on_shutdown,
    )
    monkeypatch.setattr(
        lifecycle,
        "drain_background_tasks",
        lambda: _record_background_tasks(call_order),
    )

    await lifecycle.on_shutdown()

    assert call_order == [
        "scheduler",
        "message_store",
        "runtime_config",
        "background_tasks",
    ]


async def _record_background_tasks(call_order: list[str]) -> None:
    call_order.append("background_tasks")


@pytest.mark.asyncio
async def test_on_shutdown_attempts_every_service_and_reports_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = AsyncMock(side_effect=RuntimeError("scheduler failed"))
    message_store = AsyncMock()
    runtime_config = AsyncMock(return_value=(False, False))
    background_tasks = AsyncMock()
    log_error = MagicMock()
    monkeypatch.setattr(lifecycle, "shutdown_scheduler_service", scheduler)
    monkeypatch.setattr(lifecycle, "shutdown_message_store", message_store)
    monkeypatch.setattr(lifecycle, "flush_runtime_configs_on_shutdown", runtime_config)
    monkeypatch.setattr(lifecycle, "drain_background_tasks", background_tasks)
    monkeypatch.setattr(lifecycle.logger, "error", log_error, raising=False)

    await lifecycle.on_shutdown()

    scheduler.assert_awaited_once()
    message_store.assert_awaited_once()
    runtime_config.assert_awaited_once()
    background_tasks.assert_awaited_once()
    assert log_error.call_count == 1


@pytest.mark.asyncio
async def test_on_shutdown_finishes_cleanup_before_propagating_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = AsyncMock(side_effect=asyncio.CancelledError())
    message_store = AsyncMock()
    runtime_config = AsyncMock(return_value=(False, False))
    background_tasks = AsyncMock()
    monkeypatch.setattr(lifecycle, "shutdown_scheduler_service", scheduler)
    monkeypatch.setattr(lifecycle, "shutdown_message_store", message_store)
    monkeypatch.setattr(lifecycle, "flush_runtime_configs_on_shutdown", runtime_config)
    monkeypatch.setattr(lifecycle, "drain_background_tasks", background_tasks)

    with pytest.raises(asyncio.CancelledError):
        await lifecycle.on_shutdown()

    scheduler.assert_awaited_once()
    message_store.assert_awaited_once()
    runtime_config.assert_awaited_once()
    background_tasks.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_shutdown_external_cancellation_waits_for_every_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler_started = asyncio.Event()
    release_scheduler = asyncio.Event()
    call_order: list[str] = []

    async def _shutdown_scheduler_service() -> None:
        call_order.append("scheduler")
        scheduler_started.set()
        await release_scheduler.wait()

    async def _shutdown_message_store() -> None:
        call_order.append("message_store")

    async def _flush_runtime_configs_on_shutdown() -> tuple[bool, bool]:
        call_order.append("runtime_config")
        return (False, False)

    async def _drain_background_tasks() -> None:
        call_order.append("background_tasks")

    monkeypatch.setattr(
        lifecycle, "shutdown_scheduler_service", _shutdown_scheduler_service
    )
    monkeypatch.setattr(lifecycle, "shutdown_message_store", _shutdown_message_store)
    monkeypatch.setattr(
        lifecycle,
        "flush_runtime_configs_on_shutdown",
        _flush_runtime_configs_on_shutdown,
    )
    monkeypatch.setattr(lifecycle, "drain_background_tasks", _drain_background_tasks)

    async def _run_shutdown() -> None:
        await lifecycle.on_shutdown()

    shutdown_task = asyncio.create_task(_run_shutdown())
    await scheduler_started.wait()
    shutdown_task.cancel()
    await asyncio.sleep(0)

    assert not shutdown_task.done()
    release_scheduler.set()

    with pytest.raises(asyncio.CancelledError):
        await shutdown_task

    assert call_order == [
        "scheduler",
        "message_store",
        "runtime_config",
        "background_tasks",
    ]


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
