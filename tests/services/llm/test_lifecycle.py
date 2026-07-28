from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LLMRuntimeConfig,
    PydanticAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import LLMRuntime


def make_runtime() -> LLMRuntime:
    return LLMRuntime(
        LLMRuntimeConfig(pydantic_ai=PydanticAIConfig(model="openai:gpt-5.2")),
    )


@pytest.mark.asyncio
async def test_concurrent_close_is_idempotent_and_sets_closed_state() -> None:
    runtime = make_runtime()
    runtime.profile()

    await asyncio.gather(runtime.close(), runtime.close())

    assert runtime.state == "CLOSED"
    assert not runtime._agents
    assert not runtime._profiles


@pytest.mark.asyncio
async def test_profile_after_close_raises_runtime_closing_error() -> None:
    runtime = make_runtime()
    runtime.profile()

    await runtime.close()

    with pytest.raises(RuntimeError, match="closing or closed"):
        runtime.profile()


@pytest.mark.asyncio
async def test_state_transitions_new_running_closing_closed() -> None:
    runtime = make_runtime()
    observed_states: list[str] = []

    assert runtime.state == "NEW"

    runtime.profile()
    assert runtime.state == "RUNNING"

    original_close_owned: Callable[[], Awaitable[None]] = runtime._close_owned

    async def observing_close_owned() -> None:
        observed_states.append(runtime.state)
        await original_close_owned()

    runtime._close_owned = observing_close_owned

    await runtime.close()

    assert observed_states == ["CLOSING"]
    assert runtime.state == "CLOSED"
