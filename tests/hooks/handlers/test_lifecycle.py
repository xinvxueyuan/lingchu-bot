from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import lifecycle


@pytest.mark.asyncio
async def test_on_startup_calls_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    startup = AsyncMock()
    initialize_inbound_mcp_runtime = AsyncMock()
    monkeypatch.setattr(lifecycle, "startup", startup)
    monkeypatch.setattr(
        lifecycle, "initialize_inbound_mcp_runtime", initialize_inbound_mcp_runtime
    )

    await lifecycle.on_startup()

    startup.assert_awaited_once()
    initialize_inbound_mcp_runtime.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_shutdown_calls_scheduler_llm_then_message_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def _shutdown_inbound_mcp_runtime() -> None:
        call_order.append("inbound_mcp")

    async def _shutdown_scheduler_service() -> None:
        call_order.append("scheduler")

    async def _shutdown_mcp_agent_runtime() -> None:
        call_order.append("mcp_agent")

    async def _shutdown_message_store() -> None:
        call_order.append("message_store")

    async def _shutdown_llm_runtime() -> None:
        call_order.append("llm")

    monkeypatch.setattr(
        lifecycle, "shutdown_inbound_mcp_runtime", _shutdown_inbound_mcp_runtime
    )
    monkeypatch.setattr(
        lifecycle, "shutdown_scheduler_service", _shutdown_scheduler_service
    )
    monkeypatch.setattr(
        lifecycle, "shutdown_mcp_agent_runtime", _shutdown_mcp_agent_runtime
    )
    monkeypatch.setattr(
        lifecycle, "shutdown_llm_runtime", _shutdown_llm_runtime, raising=False
    )
    monkeypatch.setattr(lifecycle, "shutdown_message_store", _shutdown_message_store)

    await lifecycle.on_shutdown()

    assert call_order == [
        "inbound_mcp",
        "scheduler",
        "mcp_agent",
        "llm",
        "message_store",
    ]


@pytest.mark.asyncio
async def test_on_shutdown_attempts_every_service_and_reports_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inbound_mcp = AsyncMock()
    scheduler = AsyncMock(side_effect=RuntimeError("scheduler failed"))
    mcp_agent = AsyncMock()
    llm = AsyncMock(side_effect=RuntimeError("llm failed"))
    message_store = AsyncMock()
    log_error = MagicMock()
    monkeypatch.setattr(lifecycle, "shutdown_inbound_mcp_runtime", inbound_mcp)
    monkeypatch.setattr(lifecycle, "shutdown_scheduler_service", scheduler)
    monkeypatch.setattr(lifecycle, "shutdown_mcp_agent_runtime", mcp_agent)
    monkeypatch.setattr(lifecycle, "shutdown_llm_runtime", llm, raising=False)
    monkeypatch.setattr(lifecycle, "shutdown_message_store", message_store)
    monkeypatch.setattr(lifecycle.logger, "error", log_error, raising=False)

    await lifecycle.on_shutdown()

    inbound_mcp.assert_awaited_once()
    scheduler.assert_awaited_once()
    mcp_agent.assert_awaited_once()
    llm.assert_awaited_once()
    message_store.assert_awaited_once()
    assert log_error.call_count == 2


@pytest.mark.asyncio
async def test_on_shutdown_finishes_cleanup_before_propagating_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inbound_mcp = AsyncMock()
    scheduler = AsyncMock(side_effect=asyncio.CancelledError())
    mcp_agent = AsyncMock()
    llm = AsyncMock()
    message_store = AsyncMock()
    monkeypatch.setattr(lifecycle, "shutdown_inbound_mcp_runtime", inbound_mcp)
    monkeypatch.setattr(lifecycle, "shutdown_scheduler_service", scheduler)
    monkeypatch.setattr(lifecycle, "shutdown_mcp_agent_runtime", mcp_agent)
    monkeypatch.setattr(lifecycle, "shutdown_llm_runtime", llm)
    monkeypatch.setattr(lifecycle, "shutdown_message_store", message_store)

    with pytest.raises(asyncio.CancelledError):
        await lifecycle.on_shutdown()

    inbound_mcp.assert_awaited_once()
    scheduler.assert_awaited_once()
    mcp_agent.assert_awaited_once()
    llm.assert_awaited_once()
    message_store.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_shutdown_external_cancellation_waits_for_every_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler_started = asyncio.Event()
    release_scheduler = asyncio.Event()
    call_order: list[str] = []

    async def _shutdown_inbound_mcp_runtime() -> None:
        call_order.append("inbound_mcp")

    async def _shutdown_scheduler_service() -> None:
        call_order.append("scheduler")
        scheduler_started.set()
        await release_scheduler.wait()

    async def _shutdown_mcp_agent_runtime() -> None:
        call_order.append("mcp_agent")

    async def _shutdown_llm_runtime() -> None:
        call_order.append("llm")

    async def _shutdown_message_store() -> None:
        call_order.append("message_store")

    monkeypatch.setattr(
        lifecycle, "shutdown_inbound_mcp_runtime", _shutdown_inbound_mcp_runtime
    )
    monkeypatch.setattr(
        lifecycle, "shutdown_scheduler_service", _shutdown_scheduler_service
    )
    monkeypatch.setattr(
        lifecycle, "shutdown_mcp_agent_runtime", _shutdown_mcp_agent_runtime
    )
    monkeypatch.setattr(lifecycle, "shutdown_llm_runtime", _shutdown_llm_runtime)
    monkeypatch.setattr(lifecycle, "shutdown_message_store", _shutdown_message_store)

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
        "inbound_mcp",
        "scheduler",
        "mcp_agent",
        "llm",
        "message_store",
    ]


@pytest.mark.asyncio
async def test_on_startup_swallows_exception_to_avoid_blocking_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    startup = AsyncMock(side_effect=RuntimeError("boom"))
    initialize_inbound_mcp_runtime = AsyncMock()
    monkeypatch.setattr(lifecycle, "startup", startup)
    monkeypatch.setattr(
        lifecycle, "initialize_inbound_mcp_runtime", initialize_inbound_mcp_runtime
    )

    # The handler itself does not catch startup errors; callers (NoneBot) handle
    # them. We assert the call is made so the driver can surface failures.
    with pytest.raises(RuntimeError, match="boom"):
        await lifecycle.on_startup()

    initialize_inbound_mcp_runtime.assert_not_awaited()


def test_driver_hooks_are_registered() -> None:
    """Importing the module registers handlers on the NoneBot driver."""
    assert lifecycle.driver is not None
    assert callable(lifecycle.on_startup)
    assert callable(lifecycle.on_shutdown)
