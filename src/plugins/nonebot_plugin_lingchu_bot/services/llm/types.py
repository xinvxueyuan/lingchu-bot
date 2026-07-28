"""Stable immutable value objects exposed by the project LLM runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast, override

from .security import safe_repr, safe_type_name, sanitize_message

if TYPE_CHECKING:
    from collections.abc import Sized


def _safe_length(value: object) -> int | None:
    try:
        return len(cast("Sized", value))
    except BaseException:
        return None


type LLMBackendName = Literal["pydantic_ai"]
type CapabilitySupport = Literal["supported", "unsupported", "unknown"]
type LLMEventType = Literal[
    "started",
    "text_delta",
    "tool_call_delta",
    "output_item",
    "usage",
    "completed",
    "error",
    "native",
]


@dataclass(frozen=True, slots=True, repr=False)
class LLMProfile:
    """Resolved administrator-controlled configuration for the Pydantic AI agent."""

    name: str
    backend: LLMBackendName
    model: str
    base_url: str | None = None
    api_key: str | None = None
    timeout: float = 60.0
    max_retries: int = 2

    @override
    def __repr__(self) -> str:
        public = {
            "name": sanitize_message(self.name),
            "backend": self.backend,
            "model": sanitize_message(self.model),
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }
        return f"LLMProfile({safe_repr(public)})"


@dataclass(frozen=True, slots=True)
class LLMUsage:
    """Provider-neutral token and cost accounting when available."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Stable projection of a completed provider response."""

    text: str | None
    output: tuple[object, ...]
    usage: LLMUsage | None
    request_id: str | None
    model: str | None
    backend: LLMBackendName
    raw: object

    @override
    def __repr__(self) -> str:
        output_length = _safe_length(self.output)
        return (
            "LLMResponse("
            f"text={safe_repr(self.text)}, "
            "output=<tuple:"
            f"{output_length if output_length is not None else 'unavailable'}>, "
            f"usage={'present' if self.usage is not None else 'none'}, "
            f"request_id={safe_repr(self.request_id)}, model={safe_repr(self.model)}, "
            f"backend={safe_repr(self.backend)}, raw=<{safe_type_name(self.raw)}>)"
        )


@dataclass(frozen=True, slots=True)
class LLMEvent:
    """Stable projection of one provider stream event."""

    type: LLMEventType
    data: object
    raw: object

    @override
    def __repr__(self) -> str:
        return (
            "LLMEvent("
            f"type={safe_repr(self.type)}, data=<{safe_type_name(self.data)}>, "
            f"raw=<{safe_type_name(self.raw)}>)"
        )


__all__ = [
    "CapabilitySupport",
    "LLMBackendName",
    "LLMEvent",
    "LLMEventType",
    "LLMProfile",
    "LLMResponse",
    "LLMUsage",
]
