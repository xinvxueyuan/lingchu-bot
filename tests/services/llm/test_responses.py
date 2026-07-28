from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LLMRuntimeConfig,
    ObservabilityConfig,
    PydanticAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import (
    LLMRuntime,
    _from_agent_result,
    _from_usage,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
    LLMProfile,
    LLMResponse,
    LLMUsage,
)


def make_config() -> LLMRuntimeConfig:
    return LLMRuntimeConfig(
        pydantic_ai=PydanticAIConfig(
            model="openai:gpt-5.2",
            api_key_env="LLM_RESPONSES_TEST_KEY",
        ),
        observability=ObservabilityConfig(enabled=False),
    )


class RunUsageLike:
    """Minimal attribute bag matching ``pydantic_ai.usage.RunUsage`` surface."""

    def __init__(
        self,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        cache_read_tokens: int | None = None,
    ) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.cache_read_tokens = cache_read_tokens


def make_agent_run_result(
    *,
    output: object = "hello",
    run_id: object = "req-1",
    usage: Any | None = None,
) -> MagicMock:
    result = MagicMock()
    result.output = output
    result.run_id = run_id
    result.usage = usage if usage is not None else RunUsageLike()
    result.all_messages = MagicMock(return_value=[])
    return result


def make_agent(result: Any | None = None) -> MagicMock:
    agent = MagicMock()
    agent.run = AsyncMock(return_value=result)
    return agent


# ---------------------------------------------------------------------------
# LLMResponse dataclass construction
# ---------------------------------------------------------------------------


def test_llm_response_carries_text_and_backend_pydantic_ai() -> None:
    response = LLMResponse(
        text="hello",
        output=(),
        usage=None,
        request_id="req-1",
        model="openai:gpt-5.2",
        backend="pydantic_ai",
        raw=object(),
    )

    assert response.text == "hello"
    assert response.backend == "pydantic_ai"
    assert response.output == ()
    assert response.request_id == "req-1"


def test_llm_response_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    response = LLMResponse(
        text="hello",
        output=(),
        usage=None,
        request_id=None,
        model=None,
        backend="pydantic_ai",
        raw=None,
    )

    with pytest.raises(FrozenInstanceError):
        cast("Any", response).text = "mutated"


def test_llm_usage_defaults_to_none_fields() -> None:
    usage = LLMUsage()

    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.cached_tokens is None
    assert usage.reasoning_tokens is None


# ---------------------------------------------------------------------------
# _from_usage mapping
# ---------------------------------------------------------------------------


def test_from_usage_returns_none_when_no_tokens_recorded() -> None:
    assert _from_usage(cast("Any", RunUsageLike())) is None


def test_from_usage_maps_all_known_token_fields() -> None:
    usage = _from_usage(
        cast(
            "Any",
            RunUsageLike(
                input_tokens=7,
                output_tokens=5,
                total_tokens=12,
                cache_read_tokens=3,
            ),
        )
    )

    assert usage == LLMUsage(
        input_tokens=7,
        output_tokens=5,
        total_tokens=12,
        cached_tokens=3,
        reasoning_tokens=None,
    )


def test_from_usage_treats_zero_as_absent() -> None:
    """``_from_usage`` uses ``or None`` coercion, so all-zero collapses to None."""
    usage = _from_usage(
        cast(
            "Any",
            RunUsageLike(
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cache_read_tokens=0,
            ),
        )
    )

    assert usage is None


def test_from_usage_propagates_cache_read_tokens_into_cached_tokens() -> None:
    usage = _from_usage(cast("Any", RunUsageLike(cache_read_tokens=42)))

    assert usage is not None
    assert usage.cached_tokens == 42


# ---------------------------------------------------------------------------
# _from_agent_result mapping
# ---------------------------------------------------------------------------


def test_from_agent_result_returns_pydantic_ai_backend_response() -> None:
    profile = LLMProfile(name="default", backend="pydantic_ai", model="openai:gpt-5.2")
    result = make_agent_run_result(
        output="hello",
        run_id="req-1",
        usage=RunUsageLike(input_tokens=2, output_tokens=3, total_tokens=5),
    )

    response = _from_agent_result(result, profile)

    assert response.backend == "pydantic_ai"
    assert response.text == "hello"
    assert response.output == ()
    assert response.model == "openai:gpt-5.2"
    assert response.request_id == "req-1"
    assert response.usage == LLMUsage(
        input_tokens=2,
        output_tokens=3,
        total_tokens=5,
        cached_tokens=None,
        reasoning_tokens=None,
    )
    assert response.raw is result


def test_from_agent_result_coerces_non_str_output_to_str() -> None:
    profile = LLMProfile(name="default", backend="pydantic_ai", model="openai:gpt-5.2")
    result = make_agent_run_result(output=42)

    response = _from_agent_result(result, profile)

    assert response.text == "42"


def test_from_agent_result_sanitizes_request_id() -> None:
    profile = LLMProfile(name="default", backend="pydantic_ai", model="openai:gpt-5.2")
    malicious_id = "req\napi_key=super-secret" + "x" * 3000
    result = make_agent_run_result(output="hello", run_id=malicious_id)

    response = _from_agent_result(result, profile)

    assert response.request_id is not None
    assert "super-secret" not in response.request_id
    assert "\n" not in response.request_id
    assert len(response.request_id) <= 2048


def test_from_agent_result_returns_none_request_id_for_non_str_run_id() -> None:
    profile = LLMProfile(name="default", backend="pydantic_ai", model="openai:gpt-5.2")
    result = make_agent_run_result(output="hello", run_id=12345)

    response = _from_agent_result(result, profile)

    assert response.request_id is None


def test_from_agent_result_returns_none_usage_when_agent_reports_no_tokens() -> None:
    profile = LLMProfile(name="default", backend="pydantic_ai", model="openai:gpt-5.2")
    result = make_agent_run_result(output="hello", usage=RunUsageLike())

    response = _from_agent_result(result, profile)

    assert response.usage is None


# ---------------------------------------------------------------------------
# respond() integration: end-to-end _from_agent_result invocation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_returns_response_with_pydantic_ai_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_RESPONSES_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    result = make_agent_run_result(
        output="hello",
        run_id="req-1",
        usage=RunUsageLike(
            input_tokens=2,
            output_tokens=3,
            total_tokens=5,
            cache_read_tokens=1,
        ),
    )
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    response = await runtime.respond("prompt")

    assert response.backend == "pydantic_ai"
    assert response.text == "hello"
    assert response.model == "openai:gpt-5.2"
    assert response.request_id == "req-1"
    assert response.usage is not None
    assert response.usage.input_tokens == 2
    assert response.usage.output_tokens == 3
    assert response.usage.total_tokens == 5
    assert response.usage.cached_tokens == 1


@pytest.mark.asyncio
async def test_respond_request_id_is_bounded_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_RESPONSES_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    malicious_id = "req\napi_key=secret-value" + "x" * 3000
    result = make_agent_run_result(output="hello", run_id=malicious_id)
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    response = await runtime.respond("prompt")

    assert response.request_id is not None
    assert "secret-value" not in response.request_id
    assert "\n" not in response.request_id
    assert len(response.request_id) <= 2048


@pytest.mark.asyncio
async def test_respond_preserves_raw_agent_result_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_RESPONSES_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    result = make_agent_run_result(output="hello")
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    response = await runtime.respond("prompt")

    assert response.raw is result


@pytest.mark.asyncio
async def test_respond_returns_none_usage_when_agent_reports_zero_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_RESPONSES_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    result = make_agent_run_result(
        output="hello",
        usage=RunUsageLike(),
    )
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    response = await runtime.respond("prompt")

    assert response.usage is None
