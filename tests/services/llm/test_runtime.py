from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import threading
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
    LLMObservabilityConfig,
    LLMProfileConfig,
    LLMRuntimeConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.errors import (
    LLMConfigurationError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import LLMRuntime


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


def legacy() -> SimpleNamespace:
    return SimpleNamespace(ai_api_key="secret", ai_base_url=None)


def test_profile_selection_and_backend_cache_are_stable() -> None:
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()), generation=3)

    assert runtime.state == "NEW"
    assert runtime.profile().name == "default"
    assert runtime.state == "RUNNING"
    assert runtime.openai() is runtime.openai()
    with pytest.raises(LLMConfigurationError, match="backend"):
        runtime.litellm()


def test_concurrent_profile_and_backend_acquisition_returns_one_instance() -> None:
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()))

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
    runtime = LLMRuntime(config, legacy=cast("Any", legacy()))
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
    runtime = LLMRuntime(config, legacy=cast("Any", legacy()))

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
    runtime = LLMRuntime(config, legacy=cast("Any", legacy()))
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


def test_live_foreign_loop_close_is_rejected_then_rebinds_after_owner_closes() -> None:
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()))
    backend = runtime.openai()
    backend.close = AsyncMock()
    owner_started = threading.Event()
    release_owner = threading.Event()

    async def hold_owner_loop() -> None:
        await runtime._drain_retirements()
        owner_started.set()
        await asyncio.to_thread(release_owner.wait)

    thread = threading.Thread(target=lambda: asyncio.run(hold_owner_loop()))
    thread.start()
    assert owner_started.wait(timeout=5)
    try:
        with pytest.raises(RuntimeError, match="another active event loop"):
            asyncio.run(runtime.close())
        assert runtime.state == "RUNNING"
        backend.close.assert_not_awaited()
    finally:
        release_owner.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    asyncio.run(runtime.close())
    backend.close.assert_awaited_once_with()
    assert runtime.state == "CLOSED"


@pytest.mark.asyncio
async def test_close_is_idempotent_and_rejects_new_acquisition() -> None:
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()))
    backend = runtime.openai()

    await runtime.close()
    await runtime.close()

    assert backend._closed is True
    with pytest.raises(RuntimeError, match="closing or closed"):
        runtime.profile()


@pytest.mark.asyncio
async def test_control_plane_parameters_are_rejected_before_sdk_access() -> None:
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()))

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
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()))

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
    runtime = LLMRuntime(configured, legacy=cast("Any", legacy()))

    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await runtime.respond("hello")
    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await anext(runtime.stream("hello"))


@pytest.mark.asyncio
async def test_close_cancellation_does_not_cancel_owned_resource_cleanup() -> None:
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()))
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
    runtime = LLMRuntime(runtime_config(), legacy=cast("Any", legacy()))

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
