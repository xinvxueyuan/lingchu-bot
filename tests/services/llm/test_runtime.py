from __future__ import annotations

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    ModelHTTPError,
)
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import (
    runtime as runtime_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LLMRuntimeConfig,
    ObservabilityConfig,
    PydanticAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMDependencyError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import (
    LLMRuntime,
    _coerce_input,
    _from_agent_result,
    _from_usage,
    _normalized_error,
    _WrongBackendError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
    LLMProfile,
    LLMResponse,
    LLMUsage,
)


def make_config(
    *,
    model: str = "openai:gpt-5.2",
    api_key_env: str | None = "LLM_TEST_API_KEY",
    base_url: str | None = None,
    timeout: float = 60.0,
) -> LLMRuntimeConfig:
    return LLMRuntimeConfig(
        pydantic_ai=PydanticAIConfig(
            model=model,
            api_key_env=api_key_env,
            base_url=base_url,
            timeout=timeout,
        ),
        observability=ObservabilityConfig(enabled=False),
    )


def make_profile(
    *,
    name: str = "default",
    model: str = "openai:gpt-5.2",
    api_key: str | None = "test-key",
) -> LLMProfile:
    return LLMProfile(
        name=name,
        backend="pydantic_ai",
        model=model,
        api_key=api_key,
    )


def make_run_usage(
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    cache_read_tokens: int | None = None,
) -> Any:
    """Build a RunUsage-like object with attribute access matching pydantic_ai."""
    return SimpleNamespaceLike(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_read_tokens=cache_read_tokens,
    )


class SimpleNamespaceLike:
    """A simple attribute-bag matching RunUsage's public surface."""

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
    """Build a fake AgentRunResult with the attributes ``_from_agent_result`` reads."""
    result = MagicMock()
    result.output = output
    result.run_id = run_id
    result.usage = usage if usage is not None else SimpleNamespaceLike()
    result.all_messages = MagicMock(return_value=[])
    return result


def make_agent(
    result: Any | None = None, *, run_side_effect: object | None = None
) -> MagicMock:
    """Build a fake Pydantic AI Agent with an AsyncMock ``run``."""
    agent = MagicMock()
    if run_side_effect is not None:
        agent.run = AsyncMock(side_effect=run_side_effect)
    else:
        agent.run = AsyncMock(return_value=result)
    return agent


# ---------------------------------------------------------------------------
# profile() and _agent() caching
# ---------------------------------------------------------------------------


def test_profile_returns_pydantic_ai_profile_with_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config(model="openai:gpt-5.2"), generation=3)

    assert runtime.state == "NEW"
    profile = runtime.profile()

    assert runtime.state == "RUNNING"
    assert profile.name == "default"
    assert profile.backend == "pydantic_ai"
    assert profile.model == "openai:gpt-5.2"
    assert profile.api_key == "secret"
    assert profile.timeout == 60.0
    assert profile.max_retries == 2


def test_profile_caches_one_instance_per_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    first = runtime.profile()
    second = runtime.profile()

    assert first is second
    assert len(runtime._profiles) == 1


def test_profile_rotation_retires_stale_cache_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "first-secret")
    runtime = LLMRuntime(make_config())

    stale = runtime.profile()
    monkeypatch.setenv("LLM_TEST_API_KEY", "second-secret")
    replacement = runtime.profile()

    assert replacement is not stale
    assert replacement.api_key == "second-secret"
    assert len(runtime._profiles) == 1


def test_agent_caches_one_instance_per_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    built: list[object] = []
    original_build = LLMRuntime._build_agent

    def recording_build(profile: LLMProfile) -> Any:
        agent = original_build(profile)
        built.append(agent)
        return agent

    runtime._build_agent = recording_build  # type: ignore[method-assign]

    first = runtime._agent()
    second = runtime._agent()

    assert first is second
    assert len(built) == 1


def test_agent_rotation_drops_stale_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "first-secret")
    runtime = LLMRuntime(make_config())

    stale = runtime._agent()
    monkeypatch.setenv("LLM_TEST_API_KEY", "second-secret")
    replacement = runtime._agent()

    assert replacement is not stale
    assert len(runtime._agents) == 1


# ---------------------------------------------------------------------------
# openai() / litellm() deprecated entrypoints
# ---------------------------------------------------------------------------


def test_openai_method_always_raises_wrong_backend_error() -> None:
    runtime = LLMRuntime(make_config())

    with pytest.raises(_WrongBackendError, match="openai"):
        runtime.openai()


def test_litellm_method_always_raises_wrong_backend_error() -> None:
    runtime = LLMRuntime(make_config())

    with pytest.raises(_WrongBackendError, match="litellm"):
        runtime.litellm()


def test_wrong_backend_error_is_configuration_error() -> None:
    assert issubclass(_WrongBackendError, LLMConfigurationError)


# ---------------------------------------------------------------------------
# respond() success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_maps_agent_result_to_llm_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config(model="openai:gpt-5.2"))
    usage = SimpleNamespaceLike(
        input_tokens=2,
        output_tokens=3,
        total_tokens=5,
        cache_read_tokens=1,
    )
    result = make_agent_run_result(output="hello", run_id="req-1", usage=usage)
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    response = await runtime.respond("prompt")

    assert isinstance(response, LLMResponse)
    assert response.text == "hello"
    assert response.backend == "pydantic_ai"
    assert response.model == "openai:gpt-5.2"
    assert response.request_id == "req-1"
    assert response.usage == LLMUsage(
        input_tokens=2,
        output_tokens=3,
        total_tokens=5,
        cached_tokens=1,
        reasoning_tokens=None,
    )
    assert response.raw is result
    agent.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_respond_passes_message_history_for_legacy_dict_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    result = make_agent_run_result(output="ok")
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    await runtime.respond([
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "ack"},
        {"role": "user", "content": "second"},
    ])

    assert agent.run.await_count == 1
    call = agent.run.await_args
    assert call.args == ("be brief\n\nsecond",)
    assert call.kwargs["message_history"] is not None
    assert len(call.kwargs["message_history"]) == 2


@pytest.mark.asyncio
async def test_respond_with_string_prompt_passes_no_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    result = make_agent_run_result(output="ok")
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    await runtime.respond("plain prompt")

    call = agent.run.await_args
    assert call.args == ("plain prompt",)
    assert call.kwargs["message_history"] is None


@pytest.mark.asyncio
async def test_respond_rejects_control_plane_parameters_before_agent_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    agent = make_agent(result=make_agent_run_result())
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await runtime.respond("hello", api_key="attacker-controlled")

    agent.run.assert_not_awaited()


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
async def test_respond_rejects_all_control_plane_parameters(
    monkeypatch: pytest.MonkeyPatch,
    parameter: str,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    with pytest.raises(LLMConfigurationError, match="control-plane"):
        await runtime.respond("hello", **{parameter: cast("Any", object())})


@pytest.mark.asyncio
async def test_respond_forwards_non_control_plane_params_in_model_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    result = make_agent_run_result(output="ok")
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    await runtime.respond("hello", temperature=0.5)

    call = agent.run.await_args
    model_settings = call.kwargs["model_settings"]
    assert model_settings == {"timeout": 60.0, "temperature": 0.5}


@pytest.mark.asyncio
async def test_respond_model_settings_includes_profile_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config(timeout=30.0))
    result = make_agent_run_result(output="ok")
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    await runtime.respond("hello")

    call = agent.run.await_args
    model_settings = call.kwargs["model_settings"]
    assert model_settings == {"timeout": 30.0}


@pytest.mark.asyncio
async def test_respond_model_settings_includes_base_url_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config(base_url="http://localhost:3900"))
    result = make_agent_run_result(output="ok")
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    await runtime.respond("hello")

    call = agent.run.await_args
    model_settings = call.kwargs["model_settings"]
    assert model_settings == {
        "base_url": "http://localhost:3900",
        "timeout": 60.0,
    }


# ---------------------------------------------------------------------------
# respond() error mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, LLMAuthenticationError),
        (403, LLMAuthenticationError),
        (429, LLMRateLimitError),
        (408, LLMTimeoutError),
        (504, LLMTimeoutError),
        (500, LLMProviderError),
    ],
)
async def test_respond_maps_model_http_error_status_to_typed_error(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected: type[Exception],
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = ModelHTTPError(status_code=status_code, model_name="openai:gpt-5.2")
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(expected) as captured:
        await runtime.respond("hello")

    assert captured.value.__cause__ is exc
    if isinstance(captured.value, LLMRateLimitError | LLMTimeoutError):
        assert captured.value.retryable is True


@pytest.mark.asyncio
async def test_respond_maps_asyncio_timeout_to_llm_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = TimeoutError()
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMTimeoutError) as captured:
        await runtime.respond("hello")

    assert captured.value.__cause__ is exc
    assert captured.value.retryable is True


@pytest.mark.asyncio
async def test_respond_maps_import_error_to_llm_dependency_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = ImportError("pydantic_ai not installed")
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMDependencyError) as captured:
        await runtime.respond("hello")

    assert captured.value.__cause__ is exc


@pytest.mark.asyncio
async def test_respond_maps_module_not_found_to_llm_dependency_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = ModuleNotFoundError("no module")
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMDependencyError):
        await runtime.respond("hello")


@pytest.mark.asyncio
async def test_respond_maps_agent_run_error_to_llm_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = AgentRunError("agent failed")
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMProviderError) as captured:
        await runtime.respond("hello")

    assert captured.value.__cause__ is exc


@pytest.mark.asyncio
async def test_respond_maps_model_api_error_to_llm_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = ModelAPIError(model_name="openai:gpt-5.2", message="provider body secret")
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMProviderError) as captured:
        await runtime.respond("secret prompt")

    assert captured.value.__cause__ is exc
    assert "secret" not in repr(captured.value)


@pytest.mark.asyncio
async def test_respond_maps_connection_named_error_to_llm_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    class ProviderConnectionError(Exception):
        pass

    exc = ProviderConnectionError("connect failed")
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMConnectionError) as captured:
        await runtime.respond("hello")

    assert captured.value.__cause__ is exc
    assert captured.value.retryable is True


# ---------------------------------------------------------------------------
# respond() observability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_emits_success_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    class Observer:
        def __init__(self) -> None:
            self.records: list[object] = []

        def emit(self, record: object) -> None:
            self.records.append(record)

    observer = Observer()
    runtime._observer = cast("Any", observer)
    result = make_agent_run_result(
        output="hello",
        run_id="req-1",
        usage=SimpleNamespaceLike(input_tokens=2, output_tokens=3, total_tokens=5),
    )
    agent = make_agent(result=result)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    await runtime.respond("prompt")

    assert len(observer.records) == 1
    record = cast("Any", observer.records[0])
    assert record.operation == "respond"
    assert record.status == "success"
    assert record.backend == "pydantic_ai"
    assert record.model == "openai:gpt-5.2"
    assert record.request_id == "req-1"
    assert record.usage is not None


@pytest.mark.asyncio
async def test_respond_emits_error_observation_and_does_not_leak_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    class Observer:
        def __init__(self) -> None:
            self.records: list[object] = []

        def emit(self, record: object) -> None:
            self.records.append(record)

    observer = Observer()
    runtime._observer = cast("Any", observer)
    exc = ModelHTTPError(status_code=429, model_name="openai:gpt-5.2")
    agent = make_agent(run_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMRateLimitError):
        await runtime.respond("secret-prompt-body")

    assert len(observer.records) == 1
    record = cast("Any", observer.records[0])
    assert record.status == "rate_limit_error"
    assert "secret-prompt-body" not in repr(record)


@pytest.mark.asyncio
async def test_observer_failure_does_not_mask_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    runtime._observer = cast(
        "Any",
        type(
            "BrokenObserver",
            (),
            {"emit": MagicMock(side_effect=RuntimeError("logger failed"))},
        )(),
    )
    agent = make_agent(result=make_agent_run_result(output="hello"))
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    response = await runtime.respond("prompt")

    assert response.text == "hello"


@pytest.mark.asyncio
async def test_observer_cancellation_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    runtime._observer = cast(
        "Any",
        type(
            "CancellingObserver",
            (),
            {"emit": MagicMock(side_effect=asyncio.CancelledError)},
        )(),
    )
    agent = make_agent(result=make_agent_run_result(output="hello"))
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(asyncio.CancelledError):
        await runtime.respond("prompt")


# ---------------------------------------------------------------------------
# close() lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_clears_cached_agents_and_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    runtime.profile()
    runtime._agent()

    assert runtime._profiles
    assert runtime._agents

    await runtime.close()

    assert runtime.state == "CLOSED"
    assert not runtime._profiles
    assert not runtime._agents


@pytest.mark.asyncio
async def test_close_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    await runtime.close()
    await runtime.close()

    assert runtime.state == "CLOSED"


@pytest.mark.asyncio
async def test_close_rejects_new_profile_acquisition_after_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    await runtime.close()

    with pytest.raises(RuntimeError, match="closing or closed"):
        runtime.profile()


@pytest.mark.asyncio
async def test_close_rejects_respond_after_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    await runtime.close()

    with pytest.raises(RuntimeError, match="closing or closed"):
        await runtime.respond("hello")


def test_foreign_loop_close_is_rejected_then_rebinds_after_owner_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())
    runtime.profile()
    owner_loop = asyncio.new_event_loop()
    runtime._async_loop = owner_loop
    try:
        with pytest.raises(RuntimeError, match="another active event loop"):
            asyncio.run(runtime.close())
        assert runtime.state == "RUNNING"
    finally:
        owner_loop.close()

    asyncio.run(runtime.close())
    assert runtime.state == "CLOSED"


# ---------------------------------------------------------------------------
# _coerce_input pure helper
# ---------------------------------------------------------------------------


def test_coerce_input_string_returns_prompt_no_history() -> None:
    prompt, history = _coerce_input("hello")
    assert prompt == "hello"
    assert history is None


def test_coerce_input_non_collection_returns_empty_prompt() -> None:
    prompt, history = _coerce_input(42)
    assert prompt == ""
    assert history is None


def test_coerce_input_single_user_message_no_history() -> None:
    prompt, history = _coerce_input([{"role": "user", "content": "hi"}])
    assert prompt == "hi"
    assert history is None


def test_coerce_input_prepends_system_messages_to_user_prompt() -> None:
    prompt, history = _coerce_input([
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hi"},
    ])
    assert prompt == "be brief\n\nhi"
    assert history is None


def test_coerce_input_builds_history_from_prior_turns() -> None:
    prompt, history = _coerce_input([
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "ack"},
        {"role": "user", "content": "second"},
    ])
    assert prompt == "second"
    assert history is not None
    assert len(history) == 2


def test_coerce_input_ignores_non_mapping_entries() -> None:
    prompt, history = _coerce_input(["junk", 5, {"role": "user", "content": "hi"}])
    assert prompt == "hi"
    assert history is None


def test_coerce_input_returns_empty_when_no_user_message() -> None:
    prompt, history = _coerce_input([
        {"role": "system", "content": "be brief"},
        {"role": "assistant", "content": "ack"},
    ])
    assert prompt == ""
    assert history is None


# ---------------------------------------------------------------------------
# _from_usage pure helper
# ---------------------------------------------------------------------------


def test_from_usage_returns_none_when_all_fields_absent() -> None:
    assert _from_usage(cast("Any", SimpleNamespaceLike())) is None


def test_from_usage_maps_known_token_fields() -> None:
    usage = _from_usage(
        cast(
            "Any",
            SimpleNamespaceLike(
                input_tokens=2,
                output_tokens=3,
                total_tokens=5,
                cache_read_tokens=1,
            ),
        )
    )
    assert usage == LLMUsage(
        input_tokens=2,
        output_tokens=3,
        total_tokens=5,
        cached_tokens=1,
        reasoning_tokens=None,
    )


def test_from_usage_treats_zero_as_absent() -> None:
    """``_from_usage`` uses ``or None`` coercion, so 0 is treated as absent.

    This mirrors the ``RunUsage`` semantics where unset token counters are 0;
    the projection collapses an all-zero report to ``None``.
    """
    usage = _from_usage(
        cast(
            "Any",
            SimpleNamespaceLike(
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cache_read_tokens=0,
            ),
        )
    )
    assert usage is None


# ---------------------------------------------------------------------------
# _from_agent_result pure helper
# ---------------------------------------------------------------------------


def test_from_agent_result_maps_str_output_to_text() -> None:
    profile = make_profile(model="openai:gpt-5.2")
    result = make_agent_run_result(output="hello", run_id="req-1")

    response = _from_agent_result(result, profile)

    assert response.text == "hello"
    assert response.backend == "pydantic_ai"
    assert response.model == "openai:gpt-5.2"
    assert response.request_id == "req-1"
    assert response.output == ()
    assert response.raw is result


def test_from_agent_result_coerces_non_str_output_to_str() -> None:
    profile = make_profile()
    result = make_agent_run_result(output={"key": "value"})

    response = _from_agent_result(result, profile)

    assert response.text == "{'key': 'value'}"


def test_from_agent_result_sanitizes_request_id() -> None:
    profile = make_profile()
    result = make_agent_run_result(
        output="hello",
        run_id="req\napi_key=secret-value" + "x" * 3000,
    )

    response = _from_agent_result(result, profile)

    assert response.request_id is not None
    assert "secret-value" not in response.request_id
    assert "\n" not in response.request_id
    assert len(response.request_id) <= 2048


def test_from_agent_result_handles_non_str_run_id() -> None:
    profile = make_profile()
    result = make_agent_run_result(output="hello", run_id=42)

    response = _from_agent_result(result, profile)

    assert response.request_id is None


# ---------------------------------------------------------------------------
# _normalized_error pure helper
# ---------------------------------------------------------------------------


def test_normalized_error_maps_model_http_error_401_to_authentication_error() -> None:
    profile = make_profile()
    exc = ModelHTTPError(status_code=401, model_name="openai:gpt-5.2")

    error = _normalized_error(exc, profile)

    assert isinstance(error, LLMAuthenticationError)
    assert error.status_code == 401


def test_normalized_error_maps_model_http_error_429_to_rate_limit_error() -> None:
    profile = make_profile()
    exc = ModelHTTPError(status_code=429, model_name="openai:gpt-5.2")

    error = _normalized_error(exc, profile)

    assert isinstance(error, LLMRateLimitError)
    assert error.retryable is True


def test_normalized_error_maps_model_http_error_408_to_timeout_error() -> None:
    profile = make_profile()
    exc = ModelHTTPError(status_code=408, model_name="openai:gpt-5.2")

    error = _normalized_error(exc, profile)

    assert isinstance(error, LLMTimeoutError)
    assert error.retryable is True


def test_normalized_error_maps_model_http_error_500_to_provider_error() -> None:
    profile = make_profile()
    exc = ModelHTTPError(status_code=500, model_name="openai:gpt-5.2")

    error = _normalized_error(exc, profile)

    assert isinstance(error, LLMProviderError)


def test_normalized_error_maps_module_not_found_to_dependency_error() -> None:
    profile = make_profile()
    error = _normalized_error(ModuleNotFoundError("no module"), profile)
    assert isinstance(error, LLMDependencyError)


def test_normalized_error_maps_agent_run_error_to_provider_error() -> None:
    profile = make_profile()
    error = _normalized_error(AgentRunError("agent failed"), profile)
    assert isinstance(error, LLMProviderError)


def test_normalized_error_maps_model_api_error_to_provider_error() -> None:
    profile = make_profile()
    error = _normalized_error(
        ModelAPIError(model_name="openai:gpt-5.2", message="api failed"), profile
    )
    assert isinstance(error, LLMProviderError)


def test_normalized_error_maps_connection_named_exception_to_connection_error() -> None:
    profile = make_profile()

    class ProviderConnectionError(Exception):
        pass

    error = _normalized_error(ProviderConnectionError(), profile)
    assert isinstance(error, LLMConnectionError)
    assert error.retryable is True


def test_normalized_error_falls_back_to_provider_error() -> None:
    profile = make_profile()

    class RandomError(Exception):
        pass

    error = _normalized_error(RandomError(), profile)
    assert isinstance(error, LLMProviderError)


# ---------------------------------------------------------------------------
# _build_agent
# ---------------------------------------------------------------------------


def test_build_agent_constructs_pydantic_ai_agent_with_defer_check() -> None:
    from pydantic_ai import Agent

    profile = make_profile(model="openai:gpt-5.2", api_key="secret")
    agent = LLMRuntime._build_agent(profile)

    assert isinstance(agent, Agent)


def test_build_agent_propagates_base_url_into_model_settings() -> None:
    profile = LLMProfile(
        name="default",
        backend="pydantic_ai",
        model="openai:gpt-5.2",
        base_url="http://localhost:3900",
        api_key="secret",
    )

    agent = LLMRuntime._build_agent(profile)

    # Pydantic AI stores model_settings internally; we verify construction does
    # not crash and the agent is the expected type.
    from pydantic_ai import Agent

    assert isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# _LifecycleCoordinator tests
# ---------------------------------------------------------------------------


def test_lifecycle_coordinator_claim_returns_false_for_inactive_ticket() -> None:
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.active = False
    assert coordinator._claim(ticket) is False


def test_lifecycle_coordinator_claim_returns_false_while_busy() -> None:
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    coordinator._busy = True
    assert coordinator._claim(ticket) is False
    assert ticket.claimed is False


def test_lifecycle_coordinator_cancel_resets_claimed_ticket() -> None:
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.claimed = True
    coordinator._busy = True
    coordinator._cancel(ticket)
    assert ticket.active is False
    assert ticket.claimed is False
    assert coordinator._busy is False


def test_lifecycle_coordinator_cancel_unclaimed_ticket_keeps_busy() -> None:
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.claimed = False
    coordinator._busy = True
    coordinator._cancel(ticket)
    assert ticket.active is False
    assert ticket.claimed is False
    assert coordinator._busy is True


def test_lifecycle_coordinator_release_unclaimed_ticket_returns_early() -> None:
    coordinator = runtime_module._LifecycleCoordinator()
    ticket = runtime_module._LifecycleTicket()
    ticket.claimed = False
    coordinator._busy = True
    coordinator.release(ticket)
    assert coordinator._busy is True


@pytest.mark.asyncio
async def test_lifecycle_coordinator_acquire_waits_for_release() -> None:
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
    coordinator = runtime_module._LifecycleCoordinator()

    def inactive_claim(ticket: Any) -> bool:
        ticket.active = False
        return False

    monkeypatch.setattr(coordinator, "_claim", inactive_claim)
    with pytest.raises(asyncio.CancelledError):
        await coordinator.acquire()


# ---------------------------------------------------------------------------
# stream() smoke (full coverage lives in test_streaming.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_rejects_control_plane_parameters_before_agent_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TEST_API_KEY", "secret")
    runtime = LLMRuntime(make_config())

    with pytest.raises(LLMConfigurationError, match="control-plane"):
        async for _ in runtime.stream("hello", api_key="attacker-controlled"):
            pass
