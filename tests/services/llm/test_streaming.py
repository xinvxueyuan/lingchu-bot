from __future__ import annotations

import asyncio
from typing import Any, Self, cast, override
from unittest.mock import MagicMock

from pydantic_ai.exceptions import ModelHTTPError
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LLMRuntimeConfig,
    ObservabilityConfig,
    PydanticAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.errors import (
    LLMProviderError,
    LLMRateLimitError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import LLMRuntime
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
    LLMEvent,
    LLMProfile,
    LLMResponse,
    LLMUsage,
)


def make_config() -> LLMRuntimeConfig:
    return LLMRuntimeConfig(
        pydantic_ai=PydanticAIConfig(
            model="openai:gpt-5.2",
            api_key_env="LLM_STREAMING_TEST_KEY",
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


class FakeStreamedRunResult:
    """Fake ``pydantic_ai.result.StreamedRunResult`` for stream() tests."""

    def __init__(
        self,
        *,
        deltas: list[str] | None = None,
        final_output: str = "hello",
        run_id: str = "req-stream-1",
        usage: Any | None = None,
    ) -> None:
        self._deltas = list(deltas) if deltas is not None else ["hel", "lo"]
        self._final_output = final_output
        self.run_id = run_id
        self.usage = (
            usage
            if usage is not None
            else RunUsageLike(input_tokens=2, output_tokens=3, total_tokens=5)
        )
        self.closed = False

    async def stream_text(self, *, delta: bool = False) -> Any:
        for chunk in self._deltas:
            yield chunk

    async def get_output(self) -> str:
        return self._final_output

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: object,
    ) -> None:
        self.closed = True


class RecordingObserver:
    def __init__(self) -> None:
        self.records: list[object] = []

    def emit(self, record: object) -> None:
        self.records.append(record)


def make_agent_with_stream(
    stream: Any | None = None,
    *,
    run_stream_side_effect: object | None = None,
) -> MagicMock:
    agent = MagicMock()
    if run_stream_side_effect is not None:
        agent.run_stream = MagicMock(side_effect=run_stream_side_effect)
    else:
        agent.run_stream = MagicMock(return_value=stream)
    return agent


# ---------------------------------------------------------------------------
# stream() happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_projects_started_deltas_and_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    streamed = FakeStreamedRunResult(
        deltas=["hel", "lo"],
        final_output="hello",
        run_id="req-stream-1",
        usage=RunUsageLike(
            input_tokens=2,
            output_tokens=3,
            total_tokens=5,
            cache_read_tokens=1,
        ),
    )
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    events = [event async for event in runtime.stream("prompt")]

    assert [event.type for event in events] == [
        "started",
        "text_delta",
        "text_delta",
        "completed",
    ]
    assert events[0].raw is None
    assert events[1] == LLMEvent(type="text_delta", data="hel", raw=None)
    assert events[2] == LLMEvent(type="text_delta", data="lo", raw=None)
    final = cast("LLMResponse", events[-1].data)
    assert final.text == "hello"
    assert final.backend == "pydantic_ai"
    assert final.model == "openai:gpt-5.2"
    assert final.request_id == "req-stream-1"
    assert final.usage == LLMUsage(
        input_tokens=2,
        output_tokens=3,
        total_tokens=5,
        cached_tokens=1,
        reasoning_tokens=None,
    )
    assert events[-1].raw is streamed


@pytest.mark.asyncio
async def test_stream_started_event_carries_resolved_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    streamed = FakeStreamedRunResult()
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    events = [event async for event in runtime.stream("prompt")]

    started = events[0]
    assert started.type == "started"
    profile = cast("LLMProfile", started.data)
    assert profile.backend == "pydantic_ai"
    assert profile.model == "openai:gpt-5.2"


@pytest.mark.asyncio
async def test_stream_invokes_run_stream_with_user_prompt_and_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    streamed = FakeStreamedRunResult()
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    _ = [event async for event in runtime.stream("hello")]

    assert agent.run_stream.call_count == 1
    call = agent.run_stream.call_args
    assert call.args == ("hello",)
    assert call.kwargs["message_history"] is None


@pytest.mark.asyncio
async def test_stream_with_dict_input_passes_message_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    streamed = FakeStreamedRunResult()
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    _ = [
        event
        async for event in runtime.stream([
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ack"},
            {"role": "user", "content": "second"},
        ])
    ]

    call = agent.run_stream.call_args
    assert call.args == ("second",)
    assert call.kwargs["message_history"] is not None
    assert len(call.kwargs["message_history"]) == 2


@pytest.mark.asyncio
async def test_stream_forwards_non_control_plane_params_into_model_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    streamed = FakeStreamedRunResult()
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    _ = [event async for event in runtime.stream("hello", temperature=0.3)]

    call = agent.run_stream.call_args
    model_settings = call.kwargs["model_settings"]
    assert model_settings == {"timeout": 60.0, "temperature": 0.3}


@pytest.mark.asyncio
async def test_stream_rejects_control_plane_parameters_before_agent_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    agent = make_agent_with_stream(stream=FakeStreamedRunResult())
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(Exception, match="control-plane"):
        async for _ in runtime.stream("hello", api_key="attacker-controlled"):
            pass

    agent.run_stream.assert_not_called()


# ---------------------------------------------------------------------------
# stream() error mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_maps_provider_error_to_llm_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = ModelHTTPError(status_code=429, model_name="openai:gpt-5.2")
    agent = make_agent_with_stream(run_stream_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMRateLimitError) as captured:
        _ = [event async for event in runtime.stream("secret prompt")]

    assert captured.value.__cause__ is exc
    assert captured.value.retryable is True


@pytest.mark.asyncio
async def test_stream_emits_started_then_raises_on_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    exc = RuntimeError("provider boom")
    agent = make_agent_with_stream(run_stream_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    started_seen = False
    with pytest.raises(LLMProviderError):
        async for event in runtime.stream("prompt"):
            if event.type == "started":
                started_seen = True

    assert started_seen


@pytest.mark.asyncio
async def test_stream_provider_error_does_not_leak_prompt_in_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    observer = RecordingObserver()
    runtime._observer = cast("Any", observer)
    exc = RuntimeError("provider body secret")
    agent = make_agent_with_stream(run_stream_side_effect=exc)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(LLMProviderError):
        _ = [event async for event in runtime.stream("secret prompt body")]

    assert len(observer.records) == 1
    record = cast("Any", observer.records[0])
    assert record.operation == "stream"
    assert record.status == "provider_error"
    assert "secret prompt body" not in repr(record)
    assert "provider body secret" not in repr(record)


# ---------------------------------------------------------------------------
# stream() observability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_emits_success_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    observer = RecordingObserver()
    runtime._observer = cast("Any", observer)
    streamed = FakeStreamedRunResult(
        deltas=["hi"],
        final_output="hi",
        run_id="req-stream-2",
        usage=RunUsageLike(input_tokens=1, output_tokens=2, total_tokens=3),
    )
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    _ = [event async for event in runtime.stream("do-not-log-this-prompt")]

    assert len(observer.records) == 1
    record = cast("Any", observer.records[0])
    assert record.operation == "stream"
    assert record.status == "success"
    assert record.backend == "pydantic_ai"
    assert record.request_id == "req-stream-2"
    assert record.usage is not None
    assert "do-not-log-this-prompt" not in repr(record)


# ---------------------------------------------------------------------------
# stream() cancellation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_cancellation_propagates_without_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    observer = RecordingObserver()
    runtime._observer = cast("Any", observer)

    started = asyncio.Event()

    class BlockingStream(FakeStreamedRunResult):
        @override
        async def stream_text(self, *, delta: bool = False) -> Any:
            started.set()
            await asyncio.Event().wait()
            yield "unreachable"

    streamed = BlockingStream()
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    projected = runtime.stream("hello")
    first = await anext(projected)
    assert first.type == "started"

    consumer = asyncio.create_task(cast("Any", anext(projected)))
    await started.wait()
    consumer.cancel()

    with pytest.raises(asyncio.CancelledError):
        await consumer

    assert observer.records == []


@pytest.mark.asyncio
async def test_stream_observer_cancellation_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    runtime._observer = cast(
        "Any",
        type(
            "CancellingObserver",
            (),
            {"emit": MagicMock(side_effect=asyncio.CancelledError)},
        )(),
    )
    streamed = FakeStreamedRunResult()
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    with pytest.raises(asyncio.CancelledError):
        _ = [event async for event in runtime.stream("prompt")]


# ---------------------------------------------------------------------------
# stream() empty deltas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_with_no_deltas_still_emits_started_and_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    streamed = FakeStreamedRunResult(
        deltas=[],
        final_output="empty",
        run_id="req-stream-empty",
    )
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    events = [event async for event in runtime.stream("prompt")]

    assert [event.type for event in events] == ["started", "completed"]
    final = cast("LLMResponse", events[-1].data)
    assert final.text == "empty"


@pytest.mark.asyncio
async def test_stream_coerces_non_str_final_output_to_str(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_STREAMING_TEST_KEY", "secret")
    runtime = LLMRuntime(make_config())
    streamed = FakeStreamedRunResult(
        deltas=["chunk"],
        final_output=cast("Any", 42),
    )
    agent = make_agent_with_stream(stream=streamed)
    monkeypatch.setattr(runtime, "_agent", lambda _name=None: agent)

    events = [event async for event in runtime.stream("prompt")]

    final = cast("LLMResponse", events[-1].data)
    assert final.text == "42"
