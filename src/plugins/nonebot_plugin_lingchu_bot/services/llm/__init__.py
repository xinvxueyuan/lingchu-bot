"""Public LLM facade with lazy access to managed runtime components."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from .compat import (
    ChatMessage,
    LLMOptions,
    WebSearchResult,
    complete_chat,
    complete_with_web_search,
    supports_web_search,
)
from .errors import (
    EmptyLLMContentError,
    LLMError,
    LLMProviderError,
    MissingLLMContentError,
)

if TYPE_CHECKING:
    from .capabilities import CapabilityRegistry, CapabilityResult
    from .events import project_stream_event
    from .observability import LLMCallRecord, StructuredLLMObserver
    from .runtime import LLMRuntime
    from .types import LLMEvent, LLMProfile, LLMResponse, LLMUsage

_LAZY_EXPORTS = {
    "CapabilityRegistry": ("capabilities", "CapabilityRegistry"),
    "CapabilityResult": ("capabilities", "CapabilityResult"),
    "LLMCallRecord": ("observability", "LLMCallRecord"),
    "LLMEvent": ("types", "LLMEvent"),
    "LLMProfile": ("types", "LLMProfile"),
    "LLMResponse": ("types", "LLMResponse"),
    "LLMRuntime": ("runtime", "LLMRuntime"),
    "LLMUsage": ("types", "LLMUsage"),
    "StructuredLLMObserver": ("observability", "StructuredLLMObserver"),
    "project_stream_event": ("events", "project_stream_event"),
}


def __getattr__(name: str) -> object:
    """Load runtime-heavy public exports only when a caller requests them."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attribute = target
    value = getattr(import_module(f"{__name__}.{module_name}"), attribute)
    globals()[name] = value
    return value


__all__ = [
    "CapabilityRegistry",
    "CapabilityResult",
    "ChatMessage",
    "EmptyLLMContentError",
    "LLMCallRecord",
    "LLMError",
    "LLMEvent",
    "LLMOptions",
    "LLMProfile",
    "LLMProviderError",
    "LLMResponse",
    "LLMRuntime",
    "LLMUsage",
    "MissingLLMContentError",
    "StructuredLLMObserver",
    "WebSearchResult",
    "complete_chat",
    "complete_with_web_search",
    "project_stream_event",
    "supports_web_search",
]
