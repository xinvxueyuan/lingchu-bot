"""Advisory, model-aware capability probes for configured LLM backends."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.metadata import PackageNotFoundError, version
import threading
from typing import TYPE_CHECKING, Literal

from .security import sanitize_message

if TYPE_CHECKING:
    from .types import CapabilitySupport, LLMProfile

type _CapabilityCacheKey = tuple[str, str, str, str, str]
_SDK_ATTRIBUTE = "sdk"


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    """One advisory capability result from an authoritative SDK probe."""

    capability: str
    support: CapabilitySupport
    source: str
    reason: str | None = None


def _base_url_fingerprint(value: str | None) -> str:
    encoded = value.encode("utf-8", errors="replace") if value else b""
    return hashlib.sha256(encoded).hexdigest()


def _sdk_version(sdk: object) -> str:
    try:
        value = getattr(sdk, "__version__", None)
    except Exception:
        return "unknown"
    if type(value) is str:
        return sanitize_message(value)
    try:
        installed = version("litellm")
    except PackageNotFoundError:
        return "unknown"
    return sanitize_message(installed)


class CapabilityRegistry:
    """Cache advisory probes without retaining credentials or provider bodies."""

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
        """Probe a model capability; unknown never prevents a native call."""
        if profile.backend != "litellm":
            return CapabilityResult(
                capability,
                "unknown",
                "openai.model_metadata",
                "model_support_not_authoritative",
            )
        source = f"litellm.supports_{capability}"
        try:
            sdk = getattr(backend, _SDK_ATTRIBUTE)
        except Exception:
            return CapabilityResult(
                capability,
                "unknown",
                source,
                "probe_error",
            )
        key = (
            profile.backend,
            profile.model,
            _base_url_fingerprint(profile.base_url),
            _sdk_version(sdk),
            capability,
        )
        with self._lock:
            cached = self._cache.get(key)
            generation = self._generation
        if cached is not None:
            return cached
        try:
            probe = getattr(sdk, f"supports_{capability}", None)
        except Exception:
            probe = None
        if not callable(probe):
            result = CapabilityResult(
                capability,
                "unknown",
                source,
                "probe_unavailable",
            )
        else:
            try:
                value = probe(model=profile.model)
            except Exception:
                result = CapabilityResult(
                    capability,
                    "unknown",
                    source,
                    "probe_error",
                )
            else:
                support: CapabilitySupport = (
                    "supported"
                    if value is True
                    else "unsupported"
                    if value is False
                    else "unknown"
                )
                result = CapabilityResult(
                    capability,
                    support,
                    source,
                    None if support != "unknown" else "invalid_probe_result",
                )
        with self._lock:
            if generation != self._generation:
                return result
            return self._cache.setdefault(key, result)

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
