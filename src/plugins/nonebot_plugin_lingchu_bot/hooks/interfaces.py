"""Hook handler interfaces and shared context types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformContext:
    """Adapter-neutral platform identity for a Bot instance."""

    platform_id: str
    adapter_id: str
    bot_id: str
    protocol_id: str | None = None


__all__ = ["PlatformContext"]
