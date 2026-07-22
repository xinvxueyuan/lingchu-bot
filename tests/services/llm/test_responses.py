from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Literal, cast, override
from unittest.mock import AsyncMock, Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.backends import (
    _NO_CREDENTIAL_API_KEY,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
    LLMObservabilityConfig,
    LLMProfileConfig,
    LLMRuntimeConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.errors import (
    LLMProviderError,
    LLMRateLimitError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import LLMRuntime


def make_runtime(profile: LLMProfileConfig) -> LLMRuntime:
    config = LLMRuntimeConfig(
        default_profile=profile.name,
        profiles={profile.name: profile},
        router=LiteLLMRouterConfig(),
        observability=LLMObservabilityConfig(),
    )
    return LLMRuntime(config)


@pytest.mark.asyncio
async def test_openai_respond_uses_responses_and_normalizes_native_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = SimpleNamespace(
        output_text="hello",
        output=[{"type": "message"}],
        usage=SimpleNamespace(input_tokens=2, output_tokens=3, total_tokens=5),
        _request_id="req-1",
        model="gpt-result",
    )
    create = AsyncMock(return_value=raw)
    client = SimpleNamespace(
        responses=SimpleNamespace(create=create), close=AsyncMock()
    )
    module = ModuleType("openai")
    module.__dict__["AsyncOpenAI"] = Mock(return_value=client)
    monkeypatch.setitem(sys.modules, "openai", module)
    runtime = make_runtime(
        LLMProfileConfig(
            name="default",
            backend="openai",
            model="gpt-configured",
            provider_options={"temperature": 0.2},
        )
    )

    response = await runtime.respond(input="prompt", temperature=0.8)

    create.assert_awaited_once_with(
        model="gpt-configured", input="prompt", temperature=0.8
    )
    assert response.text == "hello"
    assert response.output == ({"type": "message"},)
    assert response.usage is not None
    assert response.usage.total_tokens == 5
    assert response.request_id == "req-1"
    assert response.model == "gpt-result"
    assert response.raw is raw


@pytest.mark.asyncio
async def test_usage_includes_cached_and_reasoning_token_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = SimpleNamespace(
        output_text="hello",
        output=[],
        usage=SimpleNamespace(
            input_tokens=7,
            output_tokens=5,
            total_tokens=12,
            input_tokens_details=SimpleNamespace(cached_tokens=3),
            output_tokens_details=SimpleNamespace(reasoning_tokens=2),
        ),
    )
    create = AsyncMock(return_value=raw)
    module = ModuleType("openai")
    module.__dict__["AsyncOpenAI"] = Mock(
        return_value=SimpleNamespace(
            responses=SimpleNamespace(create=create), close=AsyncMock()
        )
    )
    monkeypatch.setitem(sys.modules, "openai", module)
    runtime = make_runtime(
        LLMProfileConfig(name="default", backend="openai", model="gpt")
    )

    response = await runtime.respond(input="prompt")

    assert response.usage is not None
    assert response.usage.cached_tokens == 3
    assert response.usage.reasoning_tokens == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "operation", "input_key"),
    [("responses", "aresponses", "input"), ("chat", "acompletion", "messages")],
)
async def test_litellm_respond_selects_configured_generation_only(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    operation: str,
    input_key: str,
) -> None:
    raw = SimpleNamespace(
        output_text="hello" if mode == "responses" else None,
        output=[],
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
        usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        model="provider-model",
        id="req-lite",
    )
    selected = AsyncMock(return_value=raw)
    unselected = AsyncMock(side_effect=AssertionError("fallback attempted"))
    module = ModuleType("litellm")
    module.__dict__[operation] = selected
    module.__dict__["acompletion" if operation == "aresponses" else "aresponses"] = (
        unselected
    )
    monkeypatch.setitem(sys.modules, "litellm", module)
    runtime = make_runtime(
        LLMProfileConfig(
            name="default",
            backend="litellm",
            model="openai/gpt",
            litellm_generation=cast("Literal['responses', 'chat']", mode),
        )
    )

    response = await runtime.respond([{"role": "user", "content": "prompt"}])

    selected.assert_awaited_once_with(
        model="openai/gpt",
        timeout=60.0,
        api_key=_NO_CREDENTIAL_API_KEY,
        max_retries=2,
        **{input_key: [{"role": "user", "content": "prompt"}]},
    )
    assert selected.await_args is not None
    unselected.assert_not_awaited()
    assert response.text == "hello"
    assert response.usage is not None
    assert response.usage.total_tokens == 3


@pytest.mark.asyncio
async def test_provider_errors_are_mapped_without_leaking_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ProviderRateLimitError(Exception):
        status_code = 429
        request_id = "req-rate"

    create = AsyncMock(
        side_effect=ProviderRateLimitError("authorization=Bearer super-secret")
    )
    client = SimpleNamespace(
        responses=SimpleNamespace(create=create), close=AsyncMock()
    )
    module = ModuleType("openai")
    module.__dict__["AsyncOpenAI"] = Mock(return_value=client)
    monkeypatch.setitem(sys.modules, "openai", module)
    runtime = make_runtime(
        LLMProfileConfig(name="default", backend="openai", model="gpt")
    )

    class Observer:
        def __init__(self) -> None:
            self.records: list[object] = []

        def emit(self, record: object) -> None:
            self.records.append(record)

    observer = Observer()
    runtime._observer = cast("Any", observer)

    with pytest.raises(LLMRateLimitError) as exc_info:
        await runtime.respond("secret prompt")

    assert exc_info.value.__cause__ is create.side_effect
    assert exc_info.value.status_code == 429
    assert exc_info.value.request_id == "req-rate"
    assert "super-secret" not in str(exc_info.value)
    assert cast("Any", observer.records[-1]).status == "rate_limit_error"


@pytest.mark.asyncio
async def test_observer_failure_does_not_mask_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = SimpleNamespace(output_text="hello", output=[])
    create = AsyncMock(return_value=raw)
    module = ModuleType("openai")
    module.__dict__["AsyncOpenAI"] = Mock(
        return_value=SimpleNamespace(
            responses=SimpleNamespace(create=create), close=AsyncMock()
        )
    )
    monkeypatch.setitem(sys.modules, "openai", module)
    runtime = make_runtime(
        LLMProfileConfig(name="default", backend="openai", model="gpt")
    )
    runtime._observer = cast(
        "Any", SimpleNamespace(emit=Mock(side_effect=RuntimeError("logger failed")))
    )

    response = await runtime.respond("prompt")

    assert response.text == "hello"


@pytest.mark.asyncio
async def test_observer_failure_does_not_mask_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_error = RuntimeError("provider failed")
    create = AsyncMock(side_effect=provider_error)
    module = ModuleType("openai")
    module.__dict__["AsyncOpenAI"] = Mock(
        return_value=SimpleNamespace(
            responses=SimpleNamespace(create=create), close=AsyncMock()
        )
    )
    monkeypatch.setitem(sys.modules, "openai", module)
    runtime = make_runtime(
        LLMProfileConfig(name="default", backend="openai", model="gpt")
    )
    runtime._observer = cast(
        "Any", SimpleNamespace(emit=Mock(side_effect=RuntimeError("logger failed")))
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await runtime.respond("prompt")

    assert exc_info.value.__cause__ is provider_error


@pytest.mark.asyncio
async def test_observer_cancellation_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = SimpleNamespace(output_text="hello", output=[])
    create = AsyncMock(return_value=raw)
    module = ModuleType("openai")
    module.__dict__["AsyncOpenAI"] = Mock(
        return_value=SimpleNamespace(
            responses=SimpleNamespace(create=create), close=AsyncMock()
        )
    )
    monkeypatch.setitem(sys.modules, "openai", module)
    runtime = make_runtime(
        LLMProfileConfig(name="default", backend="openai", model="gpt")
    )
    runtime._observer = cast(
        "Any", SimpleNamespace(emit=Mock(side_effect=asyncio.CancelledError))
    )

    with pytest.raises(asyncio.CancelledError):
        await runtime.respond("prompt")


@pytest.mark.asyncio
async def test_litellm_provider_error_does_not_fallback_to_other_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = AsyncMock(side_effect=RuntimeError("provider failed"))
    fallback = AsyncMock(side_effect=AssertionError("fallback attempted"))
    module = ModuleType("litellm")
    module.__dict__["aresponses"] = selected
    module.__dict__["acompletion"] = fallback
    monkeypatch.setitem(sys.modules, "litellm", module)
    runtime = make_runtime(
        LLMProfileConfig(
            name="default",
            backend="litellm",
            model="provider/model",
            litellm_generation="responses",
        )
    )

    with pytest.raises(LLMProviderError):
        await runtime.respond(input="prompt")

    selected.assert_awaited_once()
    fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_id_is_bounded_and_sanitized_before_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_id = "req\napi_key=secret-value" + "x" * 3000
    raw = SimpleNamespace(output_text="hello", output=[], _request_id=request_id)
    create = AsyncMock(return_value=raw)
    module = ModuleType("openai")
    module.__dict__["AsyncOpenAI"] = Mock(
        return_value=SimpleNamespace(
            responses=SimpleNamespace(create=create), close=AsyncMock()
        )
    )
    monkeypatch.setitem(sys.modules, "openai", module)
    runtime = make_runtime(
        LLMProfileConfig(name="default", backend="openai", model="gpt")
    )

    response = await runtime.respond(input="prompt")

    assert response.request_id is not None
    assert "secret-value" not in response.request_id
    assert "\n" not in response.request_id
    assert len(response.request_id) <= 2048


@pytest.mark.asyncio
async def test_litellm_success_observes_sdk_retry_and_fallback_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = SimpleNamespace(
        output_text="hello",
        output=[],
        _hidden_params={
            "additional_headers": {
                "x-litellm-attempted-retries": 2,
                "x-litellm-attempted-fallbacks": 1,
                "authorization": "Bearer must-not-be-observed",
            }
        },
    )
    selected = AsyncMock(return_value=raw)
    module = ModuleType("litellm")
    module.__dict__["aresponses"] = selected
    monkeypatch.setitem(sys.modules, "litellm", module)
    runtime = make_runtime(
        LLMProfileConfig(
            name="default",
            backend="litellm",
            model="provider/model",
            litellm_generation="responses",
        )
    )

    class Observer:
        def __init__(self) -> None:
            self.records: list[object] = []

        def emit(self, record: object) -> None:
            self.records.append(record)

    observer = Observer()
    runtime._observer = cast("Any", observer)

    await runtime.respond("prompt")

    record = cast("Any", observer.records[-1])
    assert record.retry_count == 2
    assert record.fallback_count == 1
    assert "must-not-be-observed" not in repr(record)


@pytest.mark.asyncio
async def test_litellm_error_observes_sdk_retry_and_fallback_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ProviderError(Exception):
        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.metadata = {
                "attempted_retries": 3,
                "fallback_depth": 2,
                "api_key": "must-not-be-observed",
            }

    selected = AsyncMock(side_effect=ProviderError("provider failed"))
    module = ModuleType("litellm")
    module.__dict__["aresponses"] = selected
    monkeypatch.setitem(sys.modules, "litellm", module)
    runtime = make_runtime(
        LLMProfileConfig(
            name="default",
            backend="litellm",
            model="provider/model",
            litellm_generation="responses",
        )
    )

    class Observer:
        def __init__(self) -> None:
            self.records: list[object] = []

        def emit(self, record: object) -> None:
            self.records.append(record)

    observer = Observer()
    runtime._observer = cast("Any", observer)

    with pytest.raises(LLMProviderError):
        await runtime.respond("prompt")

    record = cast("Any", observer.records[-1])
    assert record.retry_count == 3
    assert record.fallback_count == 2
    assert "must-not-be-observed" not in repr(record)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("retry_count", "fallback_count"),
    [
        (-1, -1),
        (True, False),
        (2**31, 2**31),
        ("2", "1"),
    ],
)
async def test_invalid_sdk_attempt_counts_are_not_observed(
    monkeypatch: pytest.MonkeyPatch,
    retry_count: object,
    fallback_count: object,
) -> None:
    raw = SimpleNamespace(
        output_text="hello",
        output=[],
        _hidden_params={
            "additional_headers": {
                "x-litellm-attempted-retries": retry_count,
                "x-litellm-attempted-fallbacks": fallback_count,
            }
        },
    )
    selected = AsyncMock(return_value=raw)
    module = ModuleType("litellm")
    module.__dict__["aresponses"] = selected
    monkeypatch.setitem(sys.modules, "litellm", module)
    runtime = make_runtime(
        LLMProfileConfig(
            name="default",
            backend="litellm",
            model="provider/model",
            litellm_generation="responses",
        )
    )

    class Observer:
        def __init__(self) -> None:
            self.records: list[object] = []

        def emit(self, record: object) -> None:
            self.records.append(record)

    observer = Observer()
    runtime._observer = cast("Any", observer)

    await runtime.respond("prompt")

    record = cast("Any", observer.records[-1])
    assert record.retry_count is None
    assert record.fallback_count is None


@pytest.mark.asyncio
async def test_hostile_sdk_attempt_metadata_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HostileMetadata:
        @override
        def __getattribute__(self, name: str) -> object:
            raise RuntimeError(name)

    raw = SimpleNamespace(
        output_text="hello",
        output=[],
        _hidden_params=HostileMetadata(),
    )
    selected = AsyncMock(return_value=raw)
    module = ModuleType("litellm")
    module.__dict__["aresponses"] = selected
    monkeypatch.setitem(sys.modules, "litellm", module)
    runtime = make_runtime(
        LLMProfileConfig(
            name="default",
            backend="litellm",
            model="provider/model",
            litellm_generation="responses",
        )
    )

    class Observer:
        def __init__(self) -> None:
            self.records: list[object] = []

        def emit(self, record: object) -> None:
            self.records.append(record)

    observer = Observer()
    runtime._observer = cast("Any", observer)

    await runtime.respond("prompt")

    record = cast("Any", observer.records[-1])
    assert record.retry_count is None
    assert record.fallback_count is None
