"""Advisory, model-aware capability probes for the Pydantic AI agent."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .types import CapabilitySupport, LLMProfile

type _CapabilityCacheKey = tuple[str, str]

_WEB_SEARCH_PREFIXES: tuple[str, ...] = (
    "openai:",
    "anthropic:",
    "google-gla:",
    "google-vertex:",
)


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    """One advisory capability result from a model-string heuristic."""

    capability: str
    support: CapabilitySupport
    source: str
    reason: str | None = None


class CapabilityRegistry:
    """Cache advisory probes by ``(profile.model, capability)`` pair.

    The Pydantic AI integration no longer probes an SDK object directly; the
    probe is a pure heuristic over the configured model string. The cache
    survives until ``invalidate()`` is called after a runtime reload.
    """

    def __init__(self) -> None:
        self._cache: dict[_CapabilityCacheKey, CapabilityResult] = {}
        self._lock = threading.RLock()
        self._generation = 0

    def probe(
        self,
        profile: LLMProfile,
        capability: Literal["web_search"],
        *,
        backend: object,
    ) -> CapabilityResult:
        """Probe a model capability by inspecting the model string.

        The ``backend`` parameter is retained for signature compatibility with
        legacy callers (notably ``contracts.py``) but is intentionally ignored;
        Pydantic AI agents do not expose a uniform SDK probe surface.

        Args:
            profile: Resolved LLM profile (only ``model`` is consulted).
            capability: Advisory capability name; only ``"web_search"`` is
                supported.
            backend: Unused; kept for signature compatibility.

        Returns:
            A ``CapabilityResult`` whose ``support`` is ``"supported"`` when the
            model string prefix is known to support the capability via Pydantic
            AI's provider integration, ``"unknown"`` otherwise.
        """
        _ = backend
        key: _CapabilityCacheKey = (profile.model, capability)
        with self._lock:
            cached = self._cache.get(key)
            generation = self._generation
        if cached is not None:
            return cached
        result = self._probe_uncached(profile, capability)
        with self._lock:
            if generation != self._generation:
                return result
            return self._cache.setdefault(key, result)

    @staticmethod
    def _probe_uncached(
        profile: LLMProfile, capability: Literal["web_search"]
    ) -> CapabilityResult:
        if capability != "web_search":
            return CapabilityResult(
                capability,
                "unknown",
                "pydantic_ai.model_string",
                "capability_not_authoritative",
            )
        if profile.model.startswith(_WEB_SEARCH_PREFIXES):
            return CapabilityResult(
                capability,
                "supported",
                "pydantic_ai.model_string",
                None,
            )
        return CapabilityResult(
            capability,
            "unknown",
            "pydantic_ai.model_string",
            "model_capability_not_authoritative",
        )

    def invalidate(self) -> None:
        """Drop all cached probe results after configuration reload."""
        with self._lock:
            self._generation += 1
            self._cache.clear()


_default_registry = CapabilityRegistry()


def probe_capability(
    profile: LLMProfile,
    capability: Literal["web_search"],
    *,
    backend: object,
) -> CapabilityResult:
    """Probe through the process registry used by compatibility callers."""
    return _default_registry.probe(profile, capability, backend=backend)


def invalidate_capability_cache() -> None:
    """Invalidate process-level advisory results after configuration reload."""
    _default_registry.invalidate()


__all__ = [
    "CapabilityRegistry",
    "CapabilityResult",
    "invalidate_capability_cache",
    "probe_capability",
]
