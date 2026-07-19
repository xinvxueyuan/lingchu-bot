"""Signed opaque cursors for external message queries."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest, digest
from json import JSONDecodeError, dumps, loads
from typing import TYPE_CHECKING, Any, Final, Never, cast

from .contracts import (
    BotAddress,
    ContractError,
    ConversationAddress,
    ErrorCode,
    MessageCursor,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_CURSOR_VERSION: Final = 1
_DEFAULT_TTL_SECONDS: Final = 900
_MAX_TOKEN_BYTES: Final = 4096
_MIN_SECRET_BYTES: Final = 32
_POSITION_FIELD_COUNT: Final = 2
_BINDING_FIELD_COUNT: Final = 10
_INVALID_CURSOR = "invalid message cursor"
_EXPIRED_CURSOR = "message cursor expired"


@dataclass(frozen=True, slots=True)
class CursorBinding:
    """Authority and query identity a cursor cannot escape."""

    principal_id: str
    grant_id: str
    grant_revision: int
    bot: BotAddress
    conversation: ConversationAddress
    query_fingerprint: str = "messages.list_recent"


@dataclass(frozen=True, slots=True)
class CursorPosition:
    """Stable `(received_at, record_id)` position."""

    received_at: datetime
    record_id: str


@dataclass(frozen=True, slots=True)
class CursorState:
    """Verified continuation state."""

    position: CursorPosition
    window_end: CursorPosition


def _b64encode(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(f"{value}{padding}")


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _position(value: object) -> CursorPosition:
    if not isinstance(value, list) or len(value) != _POSITION_FIELD_COUNT:
        raise TypeError
    timestamp, record_id = cast("list[object]", value)
    if not isinstance(timestamp, str) or not isinstance(record_id, str):
        raise TypeError
    received_at = datetime.fromisoformat(timestamp)
    if received_at.tzinfo is None or not record_id:
        raise ValueError
    return CursorPosition(received_at.astimezone(UTC), record_id)


def _raise_invalid_cursor() -> Never:
    raise ContractError(ErrorCode.INVALID_CURSOR, _INVALID_CURSOR)


def _binding_values(binding: CursorBinding) -> list[object]:
    return [
        binding.principal_id,
        binding.grant_id,
        binding.grant_revision,
        binding.bot.platform_id,
        binding.bot.adapter_id,
        binding.bot.protocol_id,
        binding.bot.bot_id,
        binding.conversation.conversation_type,
        binding.conversation.conversation_id,
        binding.query_fingerprint,
    ]


def _decode_payload(token: str) -> tuple[str, bytes, dict[str, Any]]:
    try:
        encoded_payload, encoded_signature = token.split(".")
        signature = _b64decode(encoded_signature)
        payload = loads(_b64decode(encoded_payload))
    except (JSONDecodeError, UnicodeDecodeError, ValueError):
        _raise_invalid_cursor()
    if not isinstance(payload, dict):
        _raise_invalid_cursor()
    return encoded_payload, signature, cast("dict[str, Any]", payload)


def _verified_positions(data: dict[str, Any]) -> CursorState:
    try:
        position = _position(data["p"])
        window_end = _position(data["w"])
    except (KeyError, TypeError, ValueError):
        _raise_invalid_cursor()
    return CursorState(position, window_end)


def _validate_binding(data: dict[str, Any], expected: CursorBinding) -> None:
    binding = data.get("b")
    if not isinstance(binding, list) or len(binding) != _BINDING_FIELD_COUNT:
        _raise_invalid_cursor()
    actual = cast("list[object]", binding)
    expected_values = _binding_values(expected)
    if actual[:2] == expected_values[:2] and actual[2] != expected_values[2]:
        raise ContractError(ErrorCode.CURSOR_EXPIRED, _EXPIRED_CURSOR)
    if actual != expected_values:
        _raise_invalid_cursor()


class CursorCodec:
    """Authenticate bounded canonical cursor payloads with HMAC-SHA256."""

    def __init__(
        self,
        *,
        secret: bytes,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if (
            not isinstance(secret, bytes)
            or len(secret) < _MIN_SECRET_BYTES
            or ttl_seconds <= 0
        ):
            raise ValueError
        self._secret = secret
        self._ttl_seconds = ttl_seconds
        self._clock = clock

    def encode(
        self,
        binding: CursorBinding,
        *,
        position: CursorPosition,
        window_end: CursorPosition,
    ) -> MessageCursor:
        """Create a signed continuation token."""
        now = self._clock().astimezone(UTC)
        payload = {
            "b": [
                binding.principal_id,
                binding.grant_id,
                binding.grant_revision,
                binding.bot.platform_id,
                binding.bot.adapter_id,
                binding.bot.protocol_id,
                binding.bot.bot_id,
                binding.conversation.conversation_type,
                binding.conversation.conversation_id,
                binding.query_fingerprint,
            ],
            "exp": int((now + timedelta(seconds=self._ttl_seconds)).timestamp()),
            "p": [_timestamp(position.received_at), position.record_id],
            "v": _CURSOR_VERSION,
            "w": [_timestamp(window_end.received_at), window_end.record_id],
        }
        encoded_payload = _b64encode(
            dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        signature = _b64encode(digest(self._secret, encoded_payload.encode(), sha256))
        return MessageCursor(f"{encoded_payload}.{signature}")

    def decode(
        self,
        cursor: MessageCursor | str,
        *,
        expected: CursorBinding,
    ) -> CursorState:
        """Verify and decode a token for one expected authority and query."""
        token = cursor.value if isinstance(cursor, MessageCursor) else cursor
        if len(token.encode()) > _MAX_TOKEN_BYTES:
            _raise_invalid_cursor()
        encoded_payload, signature, data = _decode_payload(token)
        expected_signature = digest(self._secret, encoded_payload.encode(), sha256)
        if not compare_digest(signature, expected_signature):
            _raise_invalid_cursor()
        version = data.get("v")
        expires_at = data.get("exp")
        if (
            version != _CURSOR_VERSION
            or isinstance(expires_at, bool)
            or not isinstance(expires_at, int)
        ):
            _raise_invalid_cursor()
        _validate_binding(data, expected)
        if expires_at <= int(self._clock().timestamp()):
            raise ContractError(ErrorCode.CURSOR_EXPIRED, _EXPIRED_CURSOR)
        return _verified_positions(data)


__all__ = ("CursorBinding", "CursorCodec", "CursorPosition", "CursorState")
