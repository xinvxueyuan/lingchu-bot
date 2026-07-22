from __future__ import annotations

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
import os
from types import SimpleNamespace
from typing import Any, SupportsIndex, cast, override
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import (
    runtime as runtime_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
    LLMObservabilityConfig,
    LLMProfileConfig,
    LLMRuntimeConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMDependencyError,
    LLMTimeoutError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import LLMRuntime
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile


def runtime_config(*profiles: LLMProfileConfig) -> LLMRuntimeConfig:
    configured = profiles or (
        LLMProfileConfig(name="default", backend="openai", model="gpt-test"),
    )
    return LLMRuntimeConfig(
        default_profile=configured[0].name,
        profiles={profile.name: profile for profile in configured},
        router=LiteLLMRouterConfig(),
        observability=LLMObservabilityConfig(),
    )


def test_profile_selection_and_backend_cache_are_stable() -> None:
    runtime = LLMRuntime(runtime_config(), generation=3)

    assert runtime.state == "NEW"
    assert runtime.profile().name == "default"
    assert runtime.state == "RUNNING"
    assert runtime.openai() is runtime.openai()
    with pytest.raises(LLMConfigurationError, match="backend"):
        runtime.litellm()


def test_concurrent_profile_and_backend_acquisition_returns_one_instance() -> None:
    runtime = LLMRuntime(runtime_config())

    with ThreadPoolExecutor(max_workers=8) as executor:
        profiles = list(executor.map(lambda _: runtime.profile(), range(32)))
        backends = list(executor.map(lambda _: runtime.openai(), range(32)))

    assert len({id(profile) for profile in profiles}) == 1
    assert len({id(backend) for backend in backends}) == 1
    assert len(runtime._owned_backends) == 1


@pytest.mark.asyncio
async def test_rotated_credential_retires_stale_backend_before_replacement_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runtime_config(
        LLMProfileConfig(
            name="default",
            backend="openai",
            model="gpt-test",
            api_key_env="LLM_RUNTIME_ROTATION_KEY",
        )
    )
    monkeypatch.setenv("LLM_RUNTIME_ROTATION_KEY", "first-secret")
    runtime = LLMRuntime(config)
    stale = runtime.openai()
    stale.close = AsyncMock()

    monkeypatch.setenv("LLM_RUNTIME_ROTATION_KEY", "second-secret")
    replacement = runtime.openai()
    await runtime._drain_retirements()

    assert replacement is not stale
    stale.close.assert_awaited_once_with()
    assert len(runtime._backends) == 1


@pytest.mark.asyncio
async def test_rotation_without_running_loop_is_closed_during_final_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runtime_config(
        LLMProfileConfig(
            name="default",
            backend="openai",
            model="gpt-test",
            api_key_env="LLM_RUNTIME_FINAL_ROTATION_KEY",
        )
    )
    monkeypatch.setenv("LLM_RUNTIME_FINAL_ROTATION_KEY", "first-secret")
    runtime = LLMRuntime(config)

    def rotate() -> tuple[Any, Any]:
        stale = runtime.openai()
        os.environ["LLM_RUNTIME_FINAL_ROTATION_KEY"] = "second-secret"
        return stale, runtime.openai()

    with ThreadPoolExecutor(max_workers=1) as executor:
        stale, replacement = executor.submit(rotate).result()
    stale.close = AsyncMock()
    replacement.close = AsyncMock()

    await runtime.close()

    stale.close.assert_awaited_once_with()
    replacement.close.assert_awaited_once_with()


def test_rotation_from_closed_loop_is_retired_by_final_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runtime_config(
        LLMProfileConfig(
            name="default",
            backend="openai",
            model="gpt-test",
            api_key_env="LLM_RUNTIME_CROSS_LOOP_KEY",
        )
    )
    monkeypatch.setenv("LLM_RUNTIME_CROSS_LOOP_KEY", "first-secret")
    runtime = LLMRuntime(config)
    calls = 0

    async def rotate_in_first_loop() -> None:
        nonlocal calls
        stale = runtime.openai()

        async def close_stale() -> None:
            nonlocal calls
            calls += 1

        cast("Any", stale).close = close_stale
        monkeypatch.setenv("LLM_RUNTIME_CROSS_LOOP_KEY", "second-secret")
        runtime.openai()
        await asyncio.sleep(0)

    asyncio.run(rotate_in_first_loop())
    asyncio.run(runtime.close())

    assert calls == 1
    assert runtime.state == "CLOSED"


def test_open_foreign_loop_close_is_rejected_then_rebinds_after_owner_closes() -> None:
    runtime = LLMRuntime(runtime_config())
    backend = runtime.openai()
    backend.close = AsyncMock()
    owner_loop = asyncio.new_event_loop()
    runtime._async_loop = owner_loop
    try:
        with pytest.raises(RuntimeError, match="another active event loop"):
            asyncio.run(runtime.close())
        assert runtime.state == "RUNNING"
        backend.close.assert_not_awaited()
    finally:
        owner_loop.close()

    asyncio.run(runtime.close())
    backend.close.assert_awaited_once_with()
    assert runtime.state == "CLOSED"


@pytest.mark.asyncio
async def test_close_is_idempotent_and_rejects_new_acquisition() -> None:
    runtime = LLMRuntime(runtime_config())
    backend = runtime.openai()

    await runtime.close()
    await runtime.close()

    assert backend._closed is True
    with pytest.raises(RuntimeError, match="closing or closed"):
        runtime.profile()


@pytest.mark.asyncio
async def test_control_plane_parameters_are_rejected_before_sdk_access() -> None:
    runtime = LLMRuntime(runtime_config())

    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await runtime.respond("hello", api_key="attacker-controlled")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "parameter",
    [
        "api_key",
        "base_url",
        "api_base",
        "organization",
        "project",
        "transport",
        "http_client",
        "client",
        "callbacks",
        "success_callback",
        "failure_callback",
        "custom_logger",
        "max_retries",
        "retry_config",
        "fallbacks",
        "headers",
        "default_query",
    ],
)
async def test_all_stable_control_plane_parameters_are_rejected(
    parameter: str,
) -> None:
    runtime = LLMRuntime(runtime_config())

    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await runtime.respond("hello", **{parameter: cast("Any", object())})

    assert runtime.state == "NEW"


@pytest.mark.asyncio
async def test_stable_calls_defensively_reject_nested_profile_control_options() -> None:
    configured = runtime_config(
        LLMProfileConfig(
            name="default",
            backend="openai",
            model="gpt-test",
            provider_options={"nested": {"callbacks": ["capture"]}},
        )
    )
    runtime = LLMRuntime(configured)

    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await runtime.respond("hello")
    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await anext(runtime.stream("hello"))


@pytest.mark.asyncio
async def test_close_cancellation_does_not_cancel_owned_resource_cleanup() -> None:
    runtime = LLMRuntime(runtime_config())
    started = asyncio.Event()
    release = asyncio.Event()

    class Backend:
        calls = 0

        async def close(self) -> None:
            self.calls += 1
            started.set()
            await release.wait()

    backend = Backend()
    runtime._owned_backends.append(backend)
    caller = asyncio.create_task(runtime.close())
    await started.wait()
    caller.cancel()

    with pytest.raises(asyncio.CancelledError):
        await caller
    assert runtime.state == "CLOSING"
    with pytest.raises(RuntimeError, match="closing or closed"):
        runtime.openai()

    release.set()
    assert runtime._close_task is not None
    await runtime._close_task
    assert runtime.state == "CLOSED"
    assert backend.calls == 1


@pytest.mark.asyncio
async def test_backend_close_cancelled_error_preserves_ownership_for_retry() -> None:
    runtime = LLMRuntime(runtime_config())

    class Backend:
        calls = 0

        async def close(self) -> None:
            self.calls += 1
            if self.calls == 1:
                raise asyncio.CancelledError

    backend = Backend()
    runtime._owned_backends.append(backend)

    with pytest.raises(asyncio.CancelledError):
        await runtime.close()

    assert runtime.state == "CLOSING"
    assert backend in runtime._owned_backends

    await runtime.close()

    assert backend.calls == 2
    assert backend not in runtime._owned_backends
    assert runtime.state == "CLOSED"


# ---------------------------------------------------------------------------
# Helper function tests: cover pure projection helpers used by the runtime.
# ---------------------------------------------------------------------------


def test_safe_float_converts_non_negative_int_and_passes_through_float() -> None:
    """Cover _safe_float int-to-float and float passthrough for non-negative values."""
    assert runtime_module._safe_float(5) == 5.0
    assert runtime_module._safe_float(3.14) == 3.14


def test_safe_float_returns_none_for_negative_and_unsupported_types() -> None:
    assert runtime_module._safe_float(-1) is None
    assert runtime_module._safe_float(-1.5) is None
    assert runtime_module._safe_float(None) is None
    assert runtime_module._safe_float("3.14") is None


def test_stream_string_returns_none_for_none_source() -> None:
    """Cover the None source guard in _stream_string (line 180)."""
    assert runtime_module._stream_string(None, "id") is None


def test_usage_returns_none_when_usage_source_lacks_recognized_fields() -> None:
    """Cover _usage returning None when all token/cost fields are absent (line 325)."""
    raw = SimpleNamespace(usage=SimpleNamespace())
    assert runtime_module._usage(raw) is None


def test_response_text_chat_returns_none_for_empty_or_non_list_choices() -> None:
    """Cover _response_text chat branch with empty or non-list choices (line 342)."""
    assert runtime_module._response_text(SimpleNamespace(choices=[]), chat=True) is None
    assert (
        runtime_module._response_text(SimpleNamespace(choices="not-list"), chat=True)
        is None
    )


def test_normalize_response_hostile_output_becomes_empty_tuple() -> None:
    """Cover _normalize_response BaseException path when tuple() fails (lines 360-361)."""

    class HostileList(list[object]):
        @override
        def __iter__(self) -> Iterator[object]:
            raise RuntimeError("hostile iteration")

    profile = LLMProfile(name="p", backend="openai", model="m")
    raw = SimpleNamespace(output=HostileList([1, 2, 3]))
    response = runtime_module._normalize_response(raw, profile=profile, chat=False)
    assert response.output == ()


def test_terminal_text_chat_branch_covers_all_choice_states() -> None:
    """Cover _terminal_text chat branch across choices-present states (lines 382-397)."""
    # choices not present -> (False, None)
    assert runtime_module._terminal_text(SimpleNamespace(), chat=True) == (False, None)
    # choices present but not list/tuple -> (True, None)
    assert runtime_module._terminal_text(
        SimpleNamespace(choices="not-list"), chat=True
    ) == (True, None)
    # choices present, empty list -> (True, None)
    assert runtime_module._terminal_text(SimpleNamespace(choices=[]), chat=True) == (
        True,
        None,
    )
    # choices present, first choice has message with string content -> (True, "hello")
    assert runtime_module._terminal_text(
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))]
        ),
        chat=True,
    ) == (True, "hello")
    # choices present, first choice has message with non-string content -> (True, None)
    assert runtime_module._terminal_text(
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=123))]
        ),
        chat=True,
    ) == (True, None)
    # choices present, first choice has no message -> (False, None)
    assert runtime_module._terminal_text(
        SimpleNamespace(choices=[SimpleNamespace()]), chat=True
    ) == (False, None)

    # choices present, first_choice access raises BaseException -> (True, None)
    class HostileChoices(list[object]):
        @override
        def __getitem__(self, index: SupportsIndex | slice, /) -> list[object]:
            raise RuntimeError("hostile index")

    assert runtime_module._terminal_text(
        SimpleNamespace(choices=HostileChoices([1])), chat=True
    ) == (True, None)


def test_terminal_output_returns_empty_for_non_list_and_hostile_iterable() -> None:
    """Cover _terminal_output non-list (line 405) and BaseException paths (lines 410-411)."""
    # output present but not list/tuple -> (True, ())
    assert runtime_module._terminal_output(SimpleNamespace(output="not-list")) == (
        True,
        (),
    )
    # output not present -> (False, ())
    assert runtime_module._terminal_output(SimpleNamespace()) == (False, ())

    # hostile iterable -> BaseException path -> (True, ())
    class HostileOutput(list[object]):
        @override
        def __iter__(self) -> Iterator[object]:
            raise RuntimeError("hostile iteration")

    assert runtime_module._terminal_output(
        SimpleNamespace(output=HostileOutput([1, 2]))
    ) == (True, ())


def test_normalized_error_maps_module_not_found_to_dependency_error() -> None:
    """Cover _normalized_error ModuleNotFoundError -> LLMDependencyError (line 433)."""
    profile = LLMProfile(name="p", backend="openai", model="m")
    exc = ModuleNotFoundError("no module")
    error = runtime_module._normalized_error(exc, profile)
    assert isinstance(error, LLMDependencyError)


def test_normalized_error_maps_status_and_name_to_typed_errors() -> None:
    """Cover _normalized_error 401, timeout, and connection mappings (lines 435, 440-444)."""
    profile = LLMProfile(name="p", backend="openai", model="m")

    class ProviderAuthError(Exception):
        status_code = 401

    auth_error = runtime_module._normalized_error(ProviderAuthError(), profile)
    assert isinstance(auth_error, LLMAuthenticationError)

    class ProviderTimeoutError(Exception):
        pass

    timeout_error = runtime_module._normalized_error(ProviderTimeoutError(), profile)
    assert isinstance(timeout_error, LLMTimeoutError)
    assert timeout_error.retryable is True

    class ProviderConnectionError(Exception):
        pass

    connection_error = runtime_module._normalized_error(
        ProviderConnectionError(), profile
    )
    assert isinstance(connection_error, LLMConnectionError)
    assert connection_error.retryable is True


def test_member_getattr_base_exception_returns_false_none() -> None:
    """Cover _member getattr BaseException path (lines 204-205)."""

    class HostileGetattr:
        def __getattr__(self, name: str) -> object:
            raise RuntimeError("hostile getattr")

    present, value = runtime_module._member(HostileGetattr(), "missing_field")
    assert present is False
    assert value is None


# ---------------------------------------------------------------------------
# Stream and close lifecycle tests.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_rejects_control_plane_parameters_before_sdk_access() -> None:
    """Cover stream() control-plane parameter rejection (line 663)."""
    runtime = LLMRuntime(runtime_config())
    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await anext(runtime.stream("hello", api_key="attacker-controlled"))


@pytest.mark.asyncio
async def test_enter_stream_rejects_non_awaitable_aenter_result() -> None:
    """Cover _InvalidStreamContextError when __aenter__ returns non-awaitable (lines 165, 753)."""

    class SyncAenterStream:
        def __aenter__(self) -> object:
            return "not-awaitable"

    with pytest.raises(TypeError, match="stream context entry must be awaitable"):
        await LLMRuntime._enter_stream(SyncAenterStream())


@pytest.mark.asyncio
async def test_close_stream_resources_deduplicates_native_stream_and_reraises() -> None:
    """Cover _close_stream_resources dedup (elif entered) and error reraise (lines 782, 789-793)."""

    class CloseStream:
        def __init__(self, *, fails: bool = False) -> None:
            self.fails = fails
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True
            if self.fails:
                raise RuntimeError("close failed")

    iterator = CloseStream(fails=True)
    entered_stream = CloseStream()
    # native_stream is the same object as iterator, entered=True
    # This triggers the ``elif entered:`` dedup branch (line 782).
    with pytest.raises(RuntimeError, match="close failed"):
        await LLMRuntime._close_stream_resources(
            iterator,
            entered_stream=entered_stream,
            iterator=iterator,
            entered=True,
        )
    assert iterator.closed
    assert entered_stream.closed


@pytest.mark.asyncio
async def test_close_stream_resources_handles_none_iterator() -> None:
    """Cover _close_stream_resources with iterator=None (line 773->775 branch)."""

    class CloseStream:
        def __init__(self) -> None:
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    native = CloseStream()
    entered = CloseStream()
    await LLMRuntime._close_stream_resources(
        native,
        entered_stream=entered,
        iterator=None,
        entered=True,
    )
    assert native.closed
    assert entered.closed


@pytest.mark.asyncio
async def test_close_stream_uses_sync_aexit_and_falls_back_to_close() -> None:
    """Cover _close_stream sync __aexit__, no-aclose fallback, and no-close exit."""

    class SyncAexitStream:
        def __init__(self) -> None:
            self.exited = False

        def __aexit__(self, *_args: object) -> None:
            self.exited = True
            # non-awaitable result covers 809->811 branch

    stream_with_sync_aexit = SyncAexitStream()
    await LLMRuntime._close_stream(stream_with_sync_aexit, entered=True)
    assert stream_with_sync_aexit.exited

    class SyncCloseStream:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True
            # non-awaitable result covers 817->exit branch

    stream_with_sync_close = SyncCloseStream()
    # entered=False, no __aexit__, no aclose, has close -> covers 814, 817->exit
    await LLMRuntime._close_stream(stream_with_sync_close, entered=False)
    assert stream_with_sync_close.closed

    class BareStream:
        pass

    # entered=False, no __aexit__, no aclose, no close -> covers 815->exit
    await LLMRuntime._close_stream(BareStream(), entered=False)


@pytest.mark.asyncio
async def test_close_stream_reraises_close_error_without_active_exception() -> None:
    """Cover _close_stream except BaseException reraise (lines 819-821)."""

    class FailingCloseStream:
        async def aclose(self) -> None:
            raise RuntimeError("close failed")

    with pytest.raises(RuntimeError, match="close failed"):
        await LLMRuntime._close_stream(FailingCloseStream(), entered=False)


# ---------------------------------------------------------------------------
# _LifecycleCoordinator tests: cover claim, cancel, acquire, and release paths.
# ---------------------------------------------------------------------------


def test_lifecycle_coordinator_claim_returns_false_for_inactive_ticket() -> None:
    """Cover _LifecycleCoordinator._claim inactive return False (line 959)."""
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.active = False
    assert coordinator._claim(ticket) is False


def test_lifecycle_coordinator_claim_returns_false_while_busy() -> None:
    """Cover _LifecycleCoordinator._claim busy return False."""
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    coordinator._busy = True
    assert coordinator._claim(ticket) is False
    assert ticket.claimed is False


def test_lifecycle_coordinator_cancel_resets_claimed_ticket() -> None:
    """Cover _LifecycleCoordinator._cancel claimed ticket path (lines 965-970)."""
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.claimed = True
    coordinator._busy = True
    coordinator._cancel(ticket)
    assert ticket.active is False
    assert ticket.claimed is False
    assert coordinator._busy is False


def test_lifecycle_coordinator_cancel_unclaimed_ticket_keeps_busy() -> None:
    """Cover _cancel unclaimed ticket path (line 967 False branch)."""
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.claimed = False
    coordinator._busy = True
    coordinator._cancel(ticket)
    assert ticket.active is False
    assert ticket.claimed is False
    assert coordinator._busy is True


def test_lifecycle_coordinator_release_unclaimed_ticket_returns_early() -> None:
    """Cover release not-claimed early return (line 987)."""
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.claimed = False
    coordinator._busy = True
    coordinator.release(ticket)
    # _busy should remain True since ticket was not claimed
    assert coordinator._busy is True


@pytest.mark.asyncio
async def test_lifecycle_coordinator_acquire_waits_for_release() -> None:
    """Cover acquire waiting without blocking the event loop."""
    coordinator = runtime_module._LifecycleCoordinator()
    first = await coordinator.acquire()
    task = asyncio.create_task(coordinator.acquire())

    await asyncio.sleep(0)

    assert not task.done()
    coordinator.release(first)
    second = await asyncio.wait_for(task, timeout=1)
    assert second.claimed is True
    coordinator.release(second)


@pytest.mark.asyncio
async def test_lifecycle_coordinator_acquire_raises_on_claim_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover acquire BaseException -> _cancel + reraise (lines 977-979)."""
    coordinator = runtime_module._LifecycleCoordinator()

    def raising_claim(_ticket: Any) -> bool:
        raise RuntimeError("claim failed")

    monkeypatch.setattr(coordinator, "_claim", raising_claim)
    with pytest.raises(RuntimeError, match="claim failed"):
        await coordinator.acquire()


@pytest.mark.asyncio
async def test_lifecycle_coordinator_acquire_raises_cancelled_when_not_claimed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover acquire not-claimed -> CancelledError (line 981)."""
    coordinator = runtime_module._LifecycleCoordinator()

    def inactive_claim(ticket: Any) -> bool:
        ticket.active = False
        return False

    monkeypatch.setattr(coordinator, "_claim", inactive_claim)
    with pytest.raises(asyncio.CancelledError):
        await coordinator.acquire()
