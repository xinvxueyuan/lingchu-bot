from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
    LLMObservabilityConfig,
    LLMProfileConfig,
    LLMRuntimeConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import LLMRuntime


def make_runtime() -> LLMRuntime:
    profile = LLMProfileConfig(name="default", backend="openai", model="gpt")
    return LLMRuntime(
        LLMRuntimeConfig(
            default_profile="default",
            profiles={"default": profile},
            router=LiteLLMRouterConfig(),
            observability=LLMObservabilityConfig(),
        ),
    )


@pytest.mark.asyncio
async def test_concurrent_close_attempts_each_resource_after_failure() -> None:
    runtime = make_runtime()

    class CloseError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("secret provider body")

    class Backend:
        def __init__(self, *, fails: bool = False) -> None:
            self.calls = 0
            self.fails = fails

        async def close(self) -> None:
            self.calls += 1
            await asyncio.sleep(0)
            if self.fails:
                raise CloseError

    first = Backend(fails=True)
    second = Backend(fails=True)
    third = Backend()
    runtime._owned_backends.extend((first, second, third))

    await asyncio.gather(runtime.close(), runtime.close())

    assert first.calls == 1
    assert second.calls == 1
    assert third.calls == 1
    assert runtime.state == "CLOSED"


@pytest.mark.asyncio
async def test_backend_creation_racing_with_close_never_creates_after_closing() -> None:
    runtime = make_runtime()
    acquired: list[object] = []

    async def acquire() -> None:
        await asyncio.sleep(0)
        with suppress(RuntimeError):
            acquired.append(runtime.openai())

    await asyncio.gather(runtime.close(), *(acquire() for _ in range(32)))

    assert runtime.state == "CLOSED"
    assert not runtime._backends
    assert not runtime._owned_backends
    with pytest.raises(RuntimeError, match="closing or closed"):
        runtime.openai()
