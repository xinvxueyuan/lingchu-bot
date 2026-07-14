from __future__ import annotations

import logging
from typing import Any, cast

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.observability import (
    LLMCallRecord,
    StructuredLLMObserver,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMUsage


def test_structured_observer_emits_only_allowlisted_metadata(
    caplog: object,
) -> None:
    observer = StructuredLLMObserver(logging.getLogger("test.llm.observer"))
    record = LLMCallRecord(
        operation="respond",
        profile="default",
        backend="openai",
        model="gpt",
        duration_ms=12.5,
        status="success",
        request_id="req-1",
        usage=LLMUsage(input_tokens=1, output_tokens=2, total_tokens=3),
    )

    log_capture = cast("Any", caplog)
    with log_capture.at_level(logging.INFO, logger="test.llm.observer"):
        observer.emit(record)

    emitted = log_capture.records[-1]
    assert emitted.getMessage() == "llm_call_completed"
    assert emitted.llm_event == {
        "operation": "respond",
        "profile": "default",
        "backend": "openai",
        "model": "gpt",
        "duration_ms": 12.5,
        "status": "success",
        "request_id": "req-1",
        "input_tokens": 1,
        "output_tokens": 2,
        "total_tokens": 3,
    }
    assert "prompt" not in vars(emitted)
    assert "output" not in vars(emitted)


def test_observer_sanitizes_hostile_metadata_and_drops_invalid_numbers(
    caplog: object,
) -> None:
    observer = StructuredLLMObserver(logging.getLogger("test.llm.hostile"))
    record = LLMCallRecord(
        operation="respond\napi_key=operation-secret",
        profile="profile\nauthorization=Bearer profile-secret",
        backend="openai",
        model="model\ntoken=model-secret" + "x" * 3000,
        duration_ms=float("nan"),
        status="provider_error\npassword=status-secret",
        request_id="req\ncookie=request-secret",
        usage=LLMUsage(
            input_tokens=cast("Any", 2**100),
            output_tokens=cast("Any", -1),
            total_tokens=3,
            cost=cast("Any", float("inf")),
            cached_tokens=1,
            reasoning_tokens=2,
        ),
        retry_count=cast("Any", object()),
        fallback_count=-1,
    )

    log_capture = cast("Any", caplog)
    with log_capture.at_level(logging.INFO, logger="test.llm.hostile"):
        observer.emit(record)

    event = log_capture.records[-1].llm_event
    rendered = repr(event)
    assert "operation-secret" not in rendered
    assert "profile-secret" not in rendered
    assert "model-secret" not in rendered
    assert "status-secret" not in rendered
    assert "request-secret" not in rendered
    assert "\n" not in rendered
    assert event["duration_ms"] == 0.0
    assert event["total_tokens"] == 3
    assert event["cached_tokens"] == 1
    assert event["reasoning_tokens"] == 2
    assert "input_tokens" not in event
    assert "output_tokens" not in event
    assert "cost" not in event
    assert "retry_count" not in event
    assert "fallback_count" not in event


def test_disabled_observer_emits_no_record(caplog: object) -> None:
    observer = StructuredLLMObserver(
        logging.getLogger("test.llm.disabled"), enabled=False
    )
    record = LLMCallRecord(
        operation="respond",
        profile="default",
        backend="openai",
        model="gpt",
        duration_ms=1.0,
        status="success",
    )

    log_capture = cast("Any", caplog)
    with log_capture.at_level(logging.INFO, logger="test.llm.disabled"):
        observer.emit(record)

    assert not log_capture.records
