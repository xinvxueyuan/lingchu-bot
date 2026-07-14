"""Lossless projection helpers for provider-native streaming events."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import cast

from .types import LLMEvent, LLMUsage


def _member(source: object, name: str) -> object | None:
    try:
        if isinstance(source, Mapping):
            return cast("Mapping[object, object]", source).get(name)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return None
    try:
        return getattr(source, name)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return None


def _first(source: object, *names: str) -> object | None:
    for name in names:
        value = _member(source, name)
        if value is not None:
            return value
    return None


def _non_negative_int(value: object | None) -> int | None:
    return value if type(value) is int and value >= 0 else None


def usage_from_native(source: object) -> LLMUsage | None:
    """Project token accounting without trusting provider-owned attributes."""
    try:
        return _usage_from_native(source)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return None


def _usage_from_native(source: object) -> LLMUsage | None:
    usage = _member(source, "usage")
    if usage is None:
        usage = source
    input_tokens = _non_negative_int(_first(usage, "input_tokens", "prompt_tokens"))
    output_tokens = _non_negative_int(
        _first(usage, "output_tokens", "completion_tokens")
    )
    total_tokens = _non_negative_int(_member(usage, "total_tokens"))
    cost_value = _first(usage, "cost", "response_cost")
    if type(cost_value) is int:
        cost = float(cost_value) if cost_value >= 0 else None
    elif type(cost_value) is float:
        cost = cost_value if cost_value >= 0 else None
    else:
        cost = None
    if all(
        value is None for value in (input_tokens, output_tokens, total_tokens, cost)
    ):
        return None
    return LLMUsage(input_tokens, output_tokens, total_tokens, cost)


def _event_name(raw: object) -> str | None:
    value = _member(raw, "type")
    return value if type(value) is str else None


def _chat_events(raw: object) -> tuple[LLMEvent, ...]:
    choices = _member(raw, "choices")
    projected: list[LLMEvent] = []
    if isinstance(choices, (list, tuple)):
        text_parts: list[str] = []
        tool_calls: list[object] = []
        for choice in choices:
            delta = _member(choice, "delta")
            content = _member(delta, "content") if delta is not None else None
            if type(content) is str:
                text_parts.append(content)
            calls = _member(delta, "tool_calls") if delta is not None else None
            if isinstance(calls, (list, tuple)):
                tool_calls.extend(calls)
        if text_parts:
            projected.append(
                LLMEvent(type="text_delta", data="".join(text_parts), raw=raw)
            )
        if tool_calls:
            projected.append(LLMEvent(type="tool_call_delta", data=tool_calls, raw=raw))
    usage = usage_from_native(raw) if _member(raw, "usage") is not None else None
    if usage is not None:
        projected.append(LLMEvent(type="usage", data=usage, raw=raw))
    return tuple(projected)


def _terminal_events(name: str, raw: object) -> tuple[LLMEvent, ...] | None:
    if name in {"error", "response.error", "response.failed"}:
        response = _member(raw, "response")
        error = _member(response, "error") if response is not None else None
        if error is None:
            error = _member(raw, "error")
        return (LLMEvent(type="error", data=error, raw=raw),)
    if name not in {"response.completed", "response.done"}:
        return None
    response = _member(raw, "response")
    projected: list[LLMEvent] = []
    usage = usage_from_native(response) if response is not None else None
    if usage is not None:
        projected.append(LLMEvent(type="usage", data=usage, raw=raw))
    projected.append(LLMEvent(type="completed", data=response, raw=raw))
    return tuple(projected)


def _delta_event(name: str, raw: object) -> LLMEvent | None:
    if name.endswith(("output_text.delta", "text.delta")):
        return LLMEvent(type="text_delta", data=_member(raw, "delta"), raw=raw)
    if any(
        marker in name
        for marker in (
            "function_call_arguments.delta",
            "custom_tool_call_input.delta",
            "mcp_call_arguments.delta",
            "tool_call.delta",
        )
    ):
        return LLMEvent(type="tool_call_delta", data=_member(raw, "delta"), raw=raw)
    return None


def project_stream_event(raw: object) -> tuple[LLMEvent, ...]:
    """Project known common fields while preserving every native event in ``raw``."""
    try:
        return _project_stream_event(raw)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return (LLMEvent(type="native", data=None, raw=raw),)


def _project_stream_event(raw: object) -> tuple[LLMEvent, ...]:
    name = _event_name(raw)
    if name is None:
        chat_events = _chat_events(raw)
        return chat_events or (LLMEvent(type="native", data=None, raw=raw),)

    events = _terminal_events(name, raw)
    if events is None:
        delta = _delta_event(name, raw)
        events = (delta,) if delta is not None else None
    if events is None and "output_item." in name:
        item = _member(raw, "item")
        events = (LLMEvent(type="output_item", data=item, raw=raw),)
    if events is None and name.endswith("usage"):
        usage = usage_from_native(raw)
        if usage is not None:
            events = (LLMEvent(type="usage", data=usage, raw=raw),)
    return events or (LLMEvent(type="native", data=None, raw=raw),)


__all__ = ["project_stream_event", "usage_from_native"]
