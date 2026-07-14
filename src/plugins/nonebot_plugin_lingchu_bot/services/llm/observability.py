"""Safe structured logging for stable LLM facade calls."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
from typing import TYPE_CHECKING

from .security import sanitize_message

if TYPE_CHECKING:
    from .types import LLMBackendName, LLMUsage


@dataclass(frozen=True, slots=True)
class LLMCallRecord:
    """Allowlisted metadata for one completed stable LLM call."""

    operation: str
    profile: str
    backend: LLMBackendName
    model: str
    duration_ms: float
    status: str
    request_id: str | None = None
    usage: LLMUsage | None = None
    retry_count: int | None = None
    fallback_count: int | None = None


class StructuredLLMObserver:
    """Emit bounded metadata without prompts, outputs, or provider bodies."""

    def __init__(
        self, logger: logging.Logger | None = None, *, enabled: bool = True
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._enabled = enabled

    def emit(self, record: LLMCallRecord) -> None:
        if not self._enabled:
            return
        duration_ms = (
            round(record.duration_ms, 3)
            if type(record.duration_ms) in {int, float}
            and math.isfinite(record.duration_ms)
            and record.duration_ms >= 0
            else 0.0
        )
        event: dict[str, object] = {
            "operation": sanitize_message(record.operation),
            "profile": sanitize_message(record.profile),
            "backend": record.backend,
            "model": sanitize_message(record.model),
            "duration_ms": duration_ms,
            "status": sanitize_message(record.status),
        }
        if type(record.request_id) is str:
            event["request_id"] = sanitize_message(record.request_id)
        if record.usage is not None:
            for key in (
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cached_tokens",
                "reasoning_tokens",
                "cost",
            ):
                value = getattr(record.usage, key)
                if (type(value) is int and 0 <= value <= 2**63 - 1) or (
                    type(value) is float and math.isfinite(value) and value >= 0
                ):
                    event[key] = value
        if type(record.retry_count) is int and 0 <= record.retry_count <= 2**31 - 1:
            event["retry_count"] = record.retry_count
        if (
            type(record.fallback_count) is int
            and 0 <= record.fallback_count <= 2**31 - 1
        ):
            event["fallback_count"] = record.fallback_count
        self._logger.info("llm_call_completed", extra={"llm_event": event})


__all__ = ["LLMCallRecord", "StructuredLLMObserver"]
