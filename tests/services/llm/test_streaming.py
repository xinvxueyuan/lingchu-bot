from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator, Mapping
from types import SimpleNamespace
from typing import Any, cast, override
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
    LLMObservabilityConfig,
    LLMProfileConfig,
    LLMRuntimeConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.errors import LLMProviderError
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.runtime import LLMRuntime
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
    LLMEvent,
    LLMResponse,
    LLMUsage,
)


def make_runtime(
    *, backend: str = "openai", generation: str = "responses"
) -> LLMRuntime:
    profile = LLMProfileConfig(
        name="default",
        backend=cast("Any", backend),
        model="model-test",
        litellm_generation=cast("Any", generation),
    )
    config = LLMRuntimeConfig(
        default_profile="default",
        profiles={"default": profile},
        router=LiteLLMRouterConfig(),
        observability=LLMObservabilityConfig(),
    )
    legacy = SimpleNamespace(ai_api_key="secret", ai_base_url=None)
    return LLMRuntime(config, legacy=cast("Any", legacy))


class FakeStream:
    def __init__(self, events: list[object]) -> None:
        self._events = iter(events)
        self.closed = False

    def __aiter__(self) -> FakeStream:
        return self

    async def __anext__(self) -> object:
        try:
            return next(self._events)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def aclose(self) -> None:
        self.closed = True


class RecordingObserver:
    def __init__(self) -> None:
        self.records: list[object] = []

    def emit(self, record: object) -> None:
        self.records.append(record)


class DistinctIteratorLayer:
    closed = False
    yielded = False

    def __aiter__(self) -> DistinctIteratorLayer:
        return self

    async def __anext__(self) -> object:
        if self.yielded:
            raise StopAsyncIteration
        self.yielded = True
        return SimpleNamespace(type="response.output_text.delta", delta="ok")

    async def aclose(self) -> None:
        self.closed = True


class DistinctEnteredStream:
    closed = False

    def __init__(self, iterator: DistinctIteratorLayer) -> None:
        self.iterator = iterator

    def __aiter__(self) -> DistinctIteratorLayer:
        return self.iterator

    async def aclose(self) -> None:
        self.closed = True


class DistinctStreamContext:
    exited = False

    def __init__(self, entered_stream: DistinctEnteredStream) -> None:
        self.entered_stream = entered_stream

    async def __aenter__(self) -> DistinctEnteredStream:
        return self.entered_stream

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: object,
    ) -> None:
        self.exited = True


@pytest.mark.asyncio
async def test_openai_stream_projects_every_stable_event_and_preserves_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = SimpleNamespace(type="response.created", response=SimpleNamespace())
    text = SimpleNamespace(type="response.output_text.delta", delta="hel")
    tool = SimpleNamespace(
        type="response.function_call_arguments.delta", delta='{"city":'
    )
    output_item = object()
    output = SimpleNamespace(type="response.output_item.added", item=output_item)
    unknown = SimpleNamespace(type="response.future.delta", value="native")
    usage = SimpleNamespace(input_tokens=2, output_tokens=3, total_tokens=5)
    native_response = SimpleNamespace(
        output_text="hello",
        output=[output_item],
        usage=usage,
        id="request-1",
        model="model-native",
    )
    completed = SimpleNamespace(type="response.completed", response=native_response)
    stream = FakeStream([created, text, tool, output, unknown, completed])
    create = AsyncMock(return_value=stream)
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(responses=SimpleNamespace(create=create))
        ),
    )

    events = [event async for event in runtime.stream("hello", temperature=0.2)]

    assert [event.type for event in events] == [
        "started",
        "native",
        "text_delta",
        "tool_call_delta",
        "output_item",
        "native",
        "usage",
        "completed",
    ]
    assert events[2] == LLMEvent(type="text_delta", data="hel", raw=text)
    assert events[3].data == '{"city":'
    assert events[4].data is output_item
    assert events[5].raw is unknown
    assert events[6].data == LLMUsage(2, 3, 5)
    final = cast("LLMResponse", events[-1].data)
    assert final.text == "hello"
    assert final.output == (output_item,)
    assert final.raw is native_response
    assert final.request_id == "request-1"
    assert stream.closed is True
    create.assert_awaited_once_with(
        temperature=0.2,
        model="model-test",
        input="hello",
        stream=True,
    )


@pytest.mark.asyncio
async def test_terminal_response_merges_only_its_present_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_item = object()
    prior_usage = SimpleNamespace(
        type="response.usage",
        input_tokens=4,
        output_tokens=6,
        total_tokens=10,
    )
    prior_metadata = SimpleNamespace(
        type="response.future.metadata",
        id="request-prior",
        model="model-prior",
    )
    terminal_response = SimpleNamespace(output_text="terminal text")
    completed = SimpleNamespace(
        type="response.completed",
        response=terminal_response,
    )
    stream = FakeStream([
        SimpleNamespace(type="response.output_text.delta", delta="prior text"),
        SimpleNamespace(type="response.output_item.added", item=output_item),
        prior_usage,
        prior_metadata,
        completed,
    ])
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=stream))
            )
        ),
    )

    events = [event async for event in runtime.stream("hello")]

    final_event = events[-1]
    final = cast("LLMResponse", final_event.data)
    assert final.text == "terminal text"
    assert final.output == (output_item,)
    assert final.usage == LLMUsage(4, 6, 10)
    assert final.request_id == "request-prior"
    assert final.model == "model-prior"
    assert final.raw is terminal_response
    assert final_event.raw is completed


@pytest.mark.asyncio
async def test_terminal_response_explicit_empty_fields_replace_assembled_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_item = object()
    terminal_response = SimpleNamespace(output_text="", output=[], id="", model="")
    stream = FakeStream([
        SimpleNamespace(type="response.output_text.delta", delta="prior text"),
        SimpleNamespace(type="response.output_item.added", item=output_item),
        SimpleNamespace(
            type="response.future.metadata", id="prior-id", model="prior-model"
        ),
        SimpleNamespace(type="response.completed", response=terminal_response),
    ])
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=stream))
            )
        ),
    )

    events = [event async for event in runtime.stream("secret prompt")]

    final = cast("LLMResponse", events[-1].data)
    assert final.text == ""
    assert final.output == ()
    assert final.request_id == ""
    assert final.model == ""


@pytest.mark.asyncio
async def test_hostile_native_member_access_degrades_to_lossless_native_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HostileMapping(Mapping[str, object]):
        @override
        def __getitem__(self, _key: str) -> object:
            raise KeyboardInterrupt

        @override
        def __iter__(self) -> Iterator[str]:
            raise KeyboardInterrupt

        @override
        def __len__(self) -> int:
            raise KeyboardInterrupt

    class HostileProperties:
        @property
        def type(self) -> str:
            raise SystemExit

        @property
        def choices(self) -> object:
            raise KeyboardInterrupt

    hostile_mapping = HostileMapping()
    hostile_properties = HostileProperties()
    stream = FakeStream([hostile_mapping, hostile_properties])
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=stream))
            )
        ),
    )

    events = [event async for event in runtime.stream("secret prompt")]

    assert [event.type for event in events] == [
        "started",
        "native",
        "native",
        "completed",
    ]
    assert events[1].raw is hostile_mapping
    assert events[2].raw is hostile_properties


@pytest.mark.asyncio
async def test_litellm_chat_stream_projects_deltas_usage_and_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="hi", tool_calls=None))],
        usage=None,
        model="chat-model",
    )
    requested_tool = AsyncMock()
    tool_call = {"function": requested_tool, "arguments": '{"x":1}'}
    tool = SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(content=None, tool_calls=[tool_call]),
                finish_reason=None,
            )
        ],
        usage=None,
    )
    usage = SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3)
    final_chunk = SimpleNamespace(choices=[], usage=usage, id="chat-request")
    stream = FakeStream([text, tool, final_chunk])
    call = AsyncMock(return_value=stream)
    runtime = make_runtime(backend="litellm", generation="chat")
    monkeypatch.setattr(
        runtime, "litellm", lambda _name=None: SimpleNamespace(call=call)
    )

    events = [event async for event in runtime.stream([{"role": "user"}])]

    assert [event.type for event in events] == [
        "started",
        "text_delta",
        "tool_call_delta",
        "usage",
        "completed",
    ]
    assert events[1].data == "hi"
    assert events[2].data == [tool_call]
    requested_tool.assert_not_awaited()
    assert cast("LLMResponse", events[-1].data).text == "hi"
    assert cast("LLMResponse", events[-1].data).usage == LLMUsage(1, 2, 3)
    assert stream.closed is True
    call.assert_awaited_once_with(
        "acompletion",
        messages=[{"role": "user"}],
        stream=True,
    )


@pytest.mark.asyncio
async def test_provider_error_event_is_data_and_does_not_gain_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_error = SimpleNamespace(
        type="response.failed", response=SimpleNamespace(error={"code": "bad"})
    )
    stream = FakeStream([native_error])
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=stream))
            )
        ),
    )

    events = [event async for event in runtime.stream("hello")]

    assert [event.type for event in events] == ["started", "error"]
    assert events[-1].raw is native_error
    assert events[-1].data == {"code": "bad"}
    assert stream.closed is True


@pytest.mark.asyncio
async def test_stream_cancellation_propagates_and_closes_iterator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()

    class BlockingStream:
        closed = False

        def __aiter__(self) -> BlockingStream:
            return self

        async def __anext__(self) -> object:
            started.set()
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

        async def aclose(self) -> None:
            self.closed = True

    stream = BlockingStream()
    runtime = make_runtime()
    observer = RecordingObserver()
    runtime._observer = cast("Any", observer)
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=stream))
            )
        ),
    )
    projected = runtime.stream("hello")
    assert (await anext(projected)).type == "started"

    async def consume_next() -> LLMEvent:
        return await anext(projected)

    consumer = asyncio.create_task(consume_next())
    await started.wait()
    consumer.cancel()

    with pytest.raises(asyncio.CancelledError):
        await consumer

    assert stream.closed is True
    assert observer.records == []


@pytest.mark.asyncio
async def test_stream_context_is_exited_and_provider_exception_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_error = ValueError("provider boom")

    class FailingContext:
        exited = False
        exit_type: type[BaseException] | None = None

        async def __aenter__(self) -> AsyncIterator[object]:
            async def failing() -> AsyncIterator[object]:
                raise provider_error
                yield

            return failing()

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            _exc: BaseException | None,
            _traceback: object,
        ) -> None:
            self.exited = True
            self.exit_type = exc_type

    context = FailingContext()
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=context))
            )
        ),
    )

    with pytest.raises(LLMProviderError) as captured:
        _ = [event async for event in runtime.stream("hello")]

    assert captured.value.__cause__ is provider_error
    assert context.exited is True
    assert context.exit_type is ValueError


@pytest.mark.asyncio
async def test_distinct_context_stream_and_iterator_are_all_released(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    iterator = DistinctIteratorLayer()
    entered_stream = DistinctEnteredStream(iterator)
    context = DistinctStreamContext(entered_stream)
    runtime = make_runtime()
    monkeypatch.setattr(
        runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=context))
            )
        ),
    )

    events = [event async for event in runtime.stream("secret prompt")]

    assert [event.type for event in events] == ["started", "text_delta", "completed"]
    assert iterator.closed is True
    assert entered_stream.closed is True
    assert context.exited is True


@pytest.mark.asyncio
async def test_stream_observability_is_allowlisted_for_success_error_and_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    success_observer = RecordingObserver()
    success_runtime = make_runtime()
    success_runtime._observer = cast("Any", success_observer)
    monkeypatch.setattr(
        success_runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(create=AsyncMock(return_value=FakeStream([])))
            )
        ),
    )

    _ = [event async for event in success_runtime.stream("do-not-log-this-prompt")]

    assert len(success_observer.records) == 1
    success_record = cast("Any", success_observer.records[0])
    assert success_record.operation == "stream"
    assert success_record.status == "success"
    assert "do-not-log-this-prompt" not in repr(success_record)

    error_observer = RecordingObserver()
    error_runtime = make_runtime()
    error_runtime._observer = cast("Any", error_observer)
    monkeypatch.setattr(
        error_runtime,
        "openai",
        lambda _name=None: SimpleNamespace(
            client=SimpleNamespace(
                responses=SimpleNamespace(
                    create=AsyncMock(side_effect=ValueError("provider body secret"))
                )
            )
        ),
    )

    with pytest.raises(LLMProviderError):
        _ = [event async for event in error_runtime.stream("another secret prompt")]

    assert len(error_observer.records) == 1
    error_record = cast("Any", error_observer.records[0])
    assert error_record.operation == "stream"
    assert error_record.status == "provider_error"
    assert "provider body secret" not in repr(error_record)
    assert "another secret prompt" not in repr(error_record)
