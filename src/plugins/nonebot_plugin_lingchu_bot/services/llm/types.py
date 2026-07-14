"""Stable immutable value objects exposed by the project LLM runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast, override

from .security import freeze_value, safe_repr, safe_type_name, sanitize_message


def _safe_length(value: object) -> int | None:
    try:
        return len(cast("Sized", value))
    except BaseException:
        return None


if TYPE_CHECKING:
    from collections.abc import Mapping, Sized

type LLMBackendName = Literal["litellm", "openai"]
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


def _empty_str_mapping() -> dict[str, str]:
    return {}


def _empty_object_mapping() -> dict[str, object]:
    return {}


def _empty_any_mapping() -> dict[str, Any]:
    return {}


@dataclass(frozen=True, slots=True, repr=False)
class LLMProfile:
    """Resolved administrator-controlled configuration for one backend."""

    name: str
    backend: LLMBackendName
    model: str
    base_url: str | None = None
    api_key: str | None = None
    organization: str | None = None
    project: str | None = None
    timeout: float = 60.0
    max_retries: int = 2
    default_headers: Mapping[str, str] = field(default_factory=_empty_str_mapping)
    default_query: Mapping[str, object] = field(default_factory=_empty_object_mapping)
    provider_options: Mapping[str, Any] = field(default_factory=_empty_any_mapping)
    litellm_generation: Literal["responses", "chat"] = "responses"
    allow_private_network: bool = False
    allow_credentials_to_custom_base_url: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_headers", freeze_value(self.default_headers))
        object.__setattr__(self, "default_query", freeze_value(self.default_query))
        object.__setattr__(
            self,
            "provider_options",
            freeze_value(self.provider_options),
        )

    @override
    def __repr__(self) -> str:
        public = {
            "name": sanitize_message(self.name),
            "backend": self.backend,
            "model": sanitize_message(self.model),
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "default_headers": f"<redacted:{len(self.default_headers)}>",
            "default_query": f"<redacted:{len(self.default_query)}>",
            "provider_options": f"<redacted:{len(self.provider_options)}>",
            "litellm_generation": self.litellm_generation,
            "allow_private_network": self.allow_private_network,
            "allow_credentials_to_custom_base_url": (
                self.allow_credentials_to_custom_base_url
            ),
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
