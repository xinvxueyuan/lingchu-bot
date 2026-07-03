"""Hook handler interfaces and shared context types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from nonebot.adapters import Event


@dataclass(frozen=True, slots=True)
class PlatformContext:
    """Adapter-neutral platform identity for a Bot instance."""

    platform_id: str
    adapter_id: str
    bot_id: str
    protocol_id: str | None = None


@dataclass(frozen=True, slots=True)
class HookContext:
    """Base context passed to hook handlers."""

    platform_context: PlatformContext | None = None


@dataclass(frozen=True, slots=True)
class EventContext(HookContext):
    """Context for event-driven hook handlers."""

    event: Event | None = None
    normalized_event: Any | None = None
    state: dict[str, Any] | None = None


class HookType(StrEnum):
    """Runtime hook capability categories."""

    LIFECYCLE = "lifecycle"
    BOT_CONNECTION = "bot_connection"
    MESSAGE_STORE = "message_store"
    API_AUDIT = "api_audit"


T_contra = TypeVar("T_contra", bound=HookContext, contravariant=True)


@runtime_checkable
class HookHandler(Protocol[T_contra]):
    """Protocol for a typed hook handler."""

    async def __call__(self, context: T_contra) -> None:
        """Handle a hook context."""
        ...


__all__ = [
    "EventContext",
    "HookContext",
    "HookHandler",
    "HookType",
    "PlatformContext",
]
