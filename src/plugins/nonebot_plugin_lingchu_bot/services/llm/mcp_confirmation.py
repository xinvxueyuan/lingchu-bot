"""Ephemeral one-time confirmation for reviewed critical MCP calls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from secrets import token_urlsafe
from threading import Lock
from types import MappingProxyType
from typing import TYPE_CHECKING

from .security import thaw_value

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class CriticalConfirmationError(ValueError):
    """Critical confirmation input is invalid."""


@dataclass(frozen=True, slots=True)
class CriticalConfirmationRequest:
    """Exact reviewed critical call awaiting a same-session reply."""

    actor_uid: str
    session_id: str
    server_name: str
    tool_name: str
    arguments: Mapping[str, object]
    ttl: timedelta


@dataclass(frozen=True, slots=True)
class CriticalConfirmationReply:
    """Scalar reply identity extracted from a NoneBot follow-up event."""

    actor_uid: str
    session_id: str
    text: str


@dataclass(frozen=True, slots=True)
class CriticalConfirmation:
    """One reviewed critical call pending same-session confirmation."""

    confirmation_id: str
    arguments_hash: str
    expires_at: datetime
    actor_uid: str
    session_id: str
    server_name: str
    tool_name: str

    def matcher_state(self) -> Mapping[str, str]:
        """Return only immutable scalar data safe for NoneBot matcher state."""
        return MappingProxyType({
            "confirmation_id": self.confirmation_id,
            "arguments_hash": self.arguments_hash,
            "expires_at": self.expires_at.isoformat(),
            "actor_uid": self.actor_uid,
            "session_id": self.session_id,
        })


class CriticalConfirmationManager:
    """Own ephemeral confirmations; a new process starts with none."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._pending: dict[str, CriticalConfirmation] = {}
        self._lock = Lock()

    def create(self, request: CriticalConfirmationRequest) -> CriticalConfirmation:
        """Create one pending confirmation bound to an exact reviewed call."""
        if (
            not request.actor_uid
            or not request.session_id
            or not request.server_name
            or not request.tool_name
            or request.ttl <= timedelta(0)
        ):
            raise CriticalConfirmationError
        state = CriticalConfirmation(
            confirmation_id=token_urlsafe(24),
            arguments_hash=_arguments_hash(request.arguments),
            expires_at=self._clock() + request.ttl,
            actor_uid=request.actor_uid,
            session_id=request.session_id,
            server_name=request.server_name,
            tool_name=request.tool_name,
        )
        with self._lock:
            self._pending[state.confirmation_id] = state
        return state

    def consume(
        self,
        state: CriticalConfirmation,
        reply: CriticalConfirmationReply,
        *,
        server_name: str,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> bool:
        """Atomically validate and consume one exact same-session confirmation."""
        with self._lock:
            pending = self._pending.get(state.confirmation_id)
            if pending is None:
                return False
            if self._clock() >= pending.expires_at:
                self._pending.pop(state.confirmation_id, None)
                return False
            valid = (
                pending == state
                and reply.text.strip().casefold() == "confirm"
                and reply.actor_uid == pending.actor_uid
                and reply.session_id == pending.session_id
                and server_name == pending.server_name
                and tool_name == pending.tool_name
                and _arguments_hash(arguments) == pending.arguments_hash
            )
            if valid:
                self._pending.pop(state.confirmation_id, None)
            return valid

    def cancel(self, confirmation_id: str) -> None:
        """Invalidate a pending confirmation without executing its call."""
        with self._lock:
            self._pending.pop(confirmation_id, None)


def _arguments_hash(arguments: Mapping[str, object]) -> str:
    canonical = json.dumps(
        thaw_value(arguments),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode()).hexdigest()


__all__ = [
    "CriticalConfirmation",
    "CriticalConfirmationError",
    "CriticalConfirmationManager",
    "CriticalConfirmationReply",
    "CriticalConfirmationRequest",
]
