from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import (
    runtime as runtime_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LLMRuntimeConfig,
    ObservabilityConfig,
    PydanticAIConfig,
)


@pytest.fixture(autouse=True)
def _reset_managed_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_module._managed_state, "runtime", None)
    monkeypatch.setattr(runtime_module._managed_state, "generation", 0)
    monkeypatch.setattr(runtime_module._managed_state, "shutting_down", False)


def make_config() -> LLMRuntimeConfig:
    return LLMRuntimeConfig(
        pydantic_ai=PydanticAIConfig(
            model="openai:gpt-5.2",
            api_key_env="LLM_RELOAD_TEST_KEY",
        ),
        observability=ObservabilityConfig(enabled=False),
    )


# ---------------------------------------------------------------------------
# get_llm_runtime / initialize_llm_runtime
# ---------------------------------------------------------------------------


def test_get_llm_runtime_lazily_builds_one_process_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = MagicMock(spec=runtime_module.LLMRuntime)
    build = MagicMock(return_value=candidate)
    monkeypatch.setattr(runtime_module, "_build_managed_runtime", build, raising=False)

    first = runtime_module.get_llm_runtime()
    second = runtime_module.get_llm_runtime()

    assert first is candidate
    assert second is candidate
    build.assert_called_once_with(generation=0)


@pytest.mark.asyncio
async def test_concurrent_initialize_publishes_one_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = MagicMock(spec=runtime_module.LLMRuntime)
    build = MagicMock(return_value=candidate)
    monkeypatch.setattr(runtime_module, "_build_managed_runtime", build)

    results = await asyncio.gather(
        *(runtime_module.initialize_llm_runtime() for _ in range(8))
    )

    assert results == [candidate] * 8
    build.assert_called_once_with(generation=0)


@pytest.mark.asyncio
async def test_invalid_first_initialize_publishes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime_module,
        "_build_managed_runtime",
        MagicMock(side_effect=ValueError("invalid initial config")),
    )

    with pytest.raises(ValueError, match="invalid initial config"):
        await runtime_module.initialize_llm_runtime()

    assert runtime_module._managed_state.runtime is None


@pytest.mark.asyncio
async def test_initialize_defers_agent_construction_until_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First initialize builds an LLMRuntime but no Pydantic AI Agent yet.

    The new runtime resolves a profile lazily on first ``profile()``/``_agent()``
    call rather than at construction time. Agents are only built when ``respond``
    or ``stream`` actually needs them.
    """
    config = make_config()
    load_config = MagicMock(return_value=config)
    monkeypatch.setattr(runtime_module, "load_llm_runtime_config", load_config)
    monkeypatch.setenv("LLM_RELOAD_TEST_KEY", "secret")

    managed = await runtime_module.initialize_llm_runtime()

    assert isinstance(managed, runtime_module.LLMRuntime)
    assert managed.state == "NEW"
    assert managed._agents == {}
    assert managed._profiles == {}

    profile = managed.profile()
    assert profile.model == "openai:gpt-5.2"
    assert profile.backend == "pydantic_ai"
    assert managed.state == "RUNNING"


# ---------------------------------------------------------------------------
# reload_llm_runtime
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_reload_swaps_then_invalidates_cache_and_closes_old(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    old = MagicMock(spec=runtime_module.LLMRuntime)
    old.close = AsyncMock(side_effect=lambda: events.append("close"))
    new = MagicMock(spec=runtime_module.LLMRuntime)
    monkeypatch.setattr(runtime_module._managed_state, "runtime", old)
    monkeypatch.setattr(runtime_module._managed_state, "generation", 4)
    monkeypatch.setattr(
        runtime_module,
        "_build_managed_runtime",
        MagicMock(return_value=new),
    )
    invalidate = MagicMock(side_effect=lambda: events.append("invalidate"))
    monkeypatch.setattr(
        runtime_module, "invalidate_capability_cache", invalidate, raising=False
    )

    result = await runtime_module.reload_llm_runtime()

    assert result is new
    assert runtime_module.get_llm_runtime() is new
    assert runtime_module._managed_state.generation == 5
    assert events == ["invalidate", "close"]


@pytest.mark.asyncio
async def test_reload_increments_generation_and_drops_old_agents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reload publishes a new runtime with a higher generation.

    The new runtime starts with empty ``_agents``/``_profiles`` caches; old
    cached agents are dropped together with the old runtime instance.
    """
    config = make_config()
    monkeypatch.setattr(runtime_module, "load_llm_runtime_config", lambda: config)
    monkeypatch.setenv("LLM_RELOAD_TEST_KEY", "secret")

    first = await runtime_module.initialize_llm_runtime()
    first_gen = first.generation
    first.profile()
    first._agent()
    assert first._agents
    assert first._profiles

    second = await runtime_module.reload_llm_runtime()

    assert second is not first
    assert second.generation == first_gen + 1
    assert second._agents == {}
    assert second._profiles == {}
    assert first.state == "CLOSED"
    assert first._agents == {}
    assert first._profiles == {}


@pytest.mark.asyncio
async def test_old_close_failure_propagates_after_new_runtime_is_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = MagicMock(spec=runtime_module.LLMRuntime)
    old.close = AsyncMock(side_effect=RuntimeError("old close failed"))
    new = MagicMock(spec=runtime_module.LLMRuntime)
    monkeypatch.setattr(runtime_module._managed_state, "runtime", old)
    monkeypatch.setattr(runtime_module._managed_state, "generation", 4)
    monkeypatch.setattr(
        runtime_module,
        "_build_managed_runtime",
        MagicMock(return_value=new),
    )
    invalidate = MagicMock()
    monkeypatch.setattr(runtime_module, "invalidate_capability_cache", invalidate)

    with pytest.raises(RuntimeError, match="old close failed"):
        await runtime_module.reload_llm_runtime()

    assert runtime_module.get_llm_runtime() is new
    assert runtime_module._managed_state.generation == 5
    invalidate.assert_called_once_with()
    old.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_reload_preserves_old_runtime_and_capability_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = MagicMock(spec=runtime_module.LLMRuntime)
    old.close = AsyncMock()
    monkeypatch.setattr(runtime_module._managed_state, "runtime", old)
    monkeypatch.setattr(runtime_module._managed_state, "generation", 2)
    monkeypatch.setattr(
        runtime_module,
        "_build_managed_runtime",
        MagicMock(side_effect=ValueError("invalid candidate")),
    )
    invalidate = MagicMock()
    monkeypatch.setattr(
        runtime_module, "invalidate_capability_cache", invalidate, raising=False
    )

    with pytest.raises(ValueError, match="invalid candidate"):
        await runtime_module.reload_llm_runtime()

    assert runtime_module.get_llm_runtime() is old
    assert runtime_module._managed_state.generation == 2
    invalidate.assert_not_called()
    old.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_two_reloads_are_serialized_through_prior_runtime_retirement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_close_started = asyncio.Event()
    release_old_close = asyncio.Event()
    first_close_started = asyncio.Event()
    release_first_close = asyncio.Event()

    async def close_old() -> None:
        old_close_started.set()
        await release_old_close.wait()

    async def close_first() -> None:
        first_close_started.set()
        await release_first_close.wait()

    old = MagicMock(spec=runtime_module.LLMRuntime)
    old.close = AsyncMock(side_effect=close_old)
    first = MagicMock(spec=runtime_module.LLMRuntime)
    first.close = AsyncMock(side_effect=close_first)
    second = MagicMock(spec=runtime_module.LLMRuntime)
    build = MagicMock(side_effect=[first, second])
    monkeypatch.setattr(runtime_module._managed_state, "runtime", old)
    monkeypatch.setattr(runtime_module, "_build_managed_runtime", build)

    first_reload = asyncio.create_task(runtime_module.reload_llm_runtime())
    await old_close_started.wait()
    second_reload = asyncio.create_task(runtime_module.reload_llm_runtime())
    await asyncio.sleep(0)

    build.assert_called_once_with(generation=1)
    assert runtime_module._managed_state.runtime is first

    release_old_close.set()
    assert await first_reload is first
    await first_close_started.wait()
    assert runtime_module._managed_state.runtime is second

    release_first_close.set()
    assert await second_reload is second
    assert runtime_module._managed_state.generation == 2
    old.close.assert_awaited_once_with()
    first.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_reload_waiting_for_shutdown_publishes_a_usable_new_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_started = asyncio.Event()
    release_close = asyncio.Event()

    async def close_old() -> None:
        close_started.set()
        await release_close.wait()

    old = MagicMock(spec=runtime_module.LLMRuntime)
    old.close = AsyncMock(side_effect=close_old)
    new = MagicMock(spec=runtime_module.LLMRuntime)
    new.state = "NEW"
    build = MagicMock(return_value=new)
    monkeypatch.setattr(runtime_module._managed_state, "runtime", old)
    monkeypatch.setattr(runtime_module, "_build_managed_runtime", build)

    shutdown = asyncio.create_task(runtime_module.shutdown_llm_runtime())
    await close_started.wait()
    reload_task = asyncio.create_task(runtime_module.reload_llm_runtime())
    await asyncio.sleep(0)

    build.assert_not_called()
    release_close.set()
    await shutdown
    result = await reload_task

    assert result is new
    assert result.state != "CLOSED"
    assert runtime_module.get_llm_runtime() is new
    build.assert_called_once_with(generation=1)


# ---------------------------------------------------------------------------
# shutdown_llm_runtime
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_detaches_and_closes_managed_runtime_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    managed = MagicMock(spec=runtime_module.LLMRuntime)
    managed.close = AsyncMock()
    monkeypatch.setattr(runtime_module._managed_state, "runtime", managed)

    await runtime_module.shutdown_llm_runtime()
    await runtime_module.shutdown_llm_runtime()

    assert runtime_module._managed_state.runtime is None
    managed.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancelled_shutdown_holds_coordinator_until_cleanup_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_started = asyncio.Event()
    release_close = asyncio.Event()

    async def close() -> None:
        close_started.set()
        await release_close.wait()

    managed = MagicMock(spec=runtime_module.LLMRuntime)
    managed.close = AsyncMock(side_effect=close)
    replacement = MagicMock(spec=runtime_module.LLMRuntime)
    monkeypatch.setattr(runtime_module._managed_state, "runtime", managed)
    monkeypatch.setattr(
        runtime_module,
        "_build_managed_runtime",
        MagicMock(return_value=replacement),
    )

    shutdown = asyncio.create_task(runtime_module.shutdown_llm_runtime())
    await close_started.wait()
    shutdown.cancel()
    initialize = asyncio.create_task(runtime_module.initialize_llm_runtime())
    await asyncio.sleep(0)

    assert not initialize.done()
    assert runtime_module._managed_state.shutting_down is True

    release_close.set()
    with pytest.raises(asyncio.CancelledError):
        await shutdown
    assert await initialize is replacement
    assert runtime_module._managed_state.shutting_down is False


@pytest.mark.asyncio
async def test_cancelled_reload_holds_coordinator_until_retirement_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_started = asyncio.Event()
    release_close = asyncio.Event()

    async def close() -> None:
        close_started.set()
        await release_close.wait()

    old = MagicMock(spec=runtime_module.LLMRuntime)
    old.close = AsyncMock(side_effect=close)
    first = MagicMock(spec=runtime_module.LLMRuntime)
    second = MagicMock(spec=runtime_module.LLMRuntime)
    monkeypatch.setattr(runtime_module._managed_state, "runtime", old)
    monkeypatch.setattr(
        runtime_module,
        "_build_managed_runtime",
        MagicMock(side_effect=[first, second]),
    )

    reload_first = asyncio.create_task(runtime_module.reload_llm_runtime())
    await close_started.wait()
    reload_first.cancel()
    reload_second = asyncio.create_task(runtime_module.reload_llm_runtime())
    await asyncio.sleep(0)

    assert not reload_second.done()

    release_close.set()
    with pytest.raises(asyncio.CancelledError):
        await reload_first
    assert await reload_second is second


@pytest.mark.asyncio
async def test_get_during_shutdown_cannot_construct_an_unowned_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_started = asyncio.Event()
    release_close = asyncio.Event()

    async def close_managed() -> None:
        close_started.set()
        await release_close.wait()

    managed = MagicMock(spec=runtime_module.LLMRuntime)
    managed.close = AsyncMock(side_effect=close_managed)
    replacement = MagicMock(spec=runtime_module.LLMRuntime)
    build = MagicMock(return_value=replacement)
    monkeypatch.setattr(runtime_module._managed_state, "runtime", managed)
    monkeypatch.setattr(runtime_module, "_build_managed_runtime", build)

    shutdown = asyncio.create_task(runtime_module.shutdown_llm_runtime())
    await close_started.wait()

    with pytest.raises(RuntimeError, match="closing or closed"):
        runtime_module.get_llm_runtime()
    build.assert_not_called()

    release_close.set()
    await shutdown

    assert runtime_module.get_llm_runtime() is replacement
    build.assert_called_once_with(generation=0)


# ---------------------------------------------------------------------------
# Cross-loop lifecycle
# ---------------------------------------------------------------------------


def test_lifecycle_coordinator_is_not_bound_to_one_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = MagicMock(spec=runtime_module.LLMRuntime)
    first.close = AsyncMock()
    second = MagicMock(spec=runtime_module.LLMRuntime)
    second.close = AsyncMock()
    build = MagicMock(side_effect=[first, second])
    monkeypatch.setattr(runtime_module, "_build_managed_runtime", build)

    assert asyncio.run(runtime_module.initialize_llm_runtime()) is first
    assert asyncio.run(runtime_module.reload_llm_runtime()) is second
    asyncio.run(runtime_module.shutdown_llm_runtime())

    first.close.assert_awaited_once_with()
    second.close.assert_awaited_once_with()


# ---------------------------------------------------------------------------
# Capability cache invalidation on reload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reload_invalidates_capability_cache_once_before_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalidate capability cache once before closing the old runtime.

    ``reload_llm_runtime`` calls ``invalidate_capability_cache`` exactly once,
    before closing the old runtime, so capability probes re-resolve against the
    new generation.
    """
    call_order: list[str] = []
    old = MagicMock(spec=runtime_module.LLMRuntime)
    old.close = AsyncMock(side_effect=lambda: call_order.append("close"))
    new = MagicMock(spec=runtime_module.LLMRuntime)

    def invalidate() -> None:
        call_order.append("invalidate")

    monkeypatch.setattr(runtime_module._managed_state, "runtime", old)
    monkeypatch.setattr(
        runtime_module,
        "_build_managed_runtime",
        MagicMock(return_value=new),
    )
    monkeypatch.setattr(
        runtime_module, "invalidate_capability_cache", invalidate, raising=False
    )

    await runtime_module.reload_llm_runtime()

    assert call_order == ["invalidate", "close"]


@pytest.mark.asyncio
async def test_reload_publishes_new_runtime_with_incremented_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config()
    monkeypatch.setattr(runtime_module, "load_llm_runtime_config", lambda: config)
    monkeypatch.setenv("LLM_RELOAD_TEST_KEY", "secret")

    first = await runtime_module.initialize_llm_runtime()
    assert first.generation == 0

    second = await runtime_module.reload_llm_runtime()
    third = await runtime_module.reload_llm_runtime()

    assert second.generation == 1
    assert third.generation == 2
    assert runtime_module._managed_state.generation == 2
    assert runtime_module.get_llm_runtime() is third


# ---------------------------------------------------------------------------
# Real-runtime integration: close() is idempotent and clears caches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_runtime_close_clears_caches_after_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real LLMRuntime (not a MagicMock) close() clears cached agents/profiles."""
    config = make_config()
    monkeypatch.setattr(runtime_module, "load_llm_runtime_config", lambda: config)
    monkeypatch.setenv("LLM_RELOAD_TEST_KEY", "secret")

    first = await runtime_module.initialize_llm_runtime()
    first.profile()
    first._agent()
    assert first._agents
    assert first._profiles

    second = await runtime_module.reload_llm_runtime()

    assert first.state == "CLOSED"
    assert first._agents == {}
    assert first._profiles == {}
    assert second.state in {"NEW", "RUNNING"}
    assert second._agents == {}
    assert second._profiles == {}
