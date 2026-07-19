from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

MAX_MESSAGE_PAGE_SIZE = 200


class ErrorCode(StrEnum):
    """Stable machine-readable domain error codes."""

    INVALID_IDENTIFIER = "invalid_identifier"
    INVALID_MESSAGE_SEGMENT = "invalid_message_segment"
    EMPTY_MESSAGE = "empty_message"
    INVALID_LIMIT = "invalid_limit"
    INVALID_CURSOR = "invalid_cursor"
    CURSOR_EXPIRED = "cursor_expired"
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_DENIED = "authorization_denied"
    BOT_NOT_FOUND = "bot_not_found"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    UNSUPPORTED_MESSAGE = "unsupported_message"
    AUDIT_UNAVAILABLE = "audit_unavailable"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    RATE_LIMITED = "rate_limited"
    PLATFORM_REJECTED = "platform_rejected"
    PLATFORM_FAILED = "platform_failed"
    INTERNAL_ERROR = "internal_error"


class CapabilityScope(StrEnum):
    """An operation class independently intersected with Resource Grants."""

    BOTS_LIST = "bots:list"
    MESSAGES_READ = "messages:read"
    MESSAGES_SEND = "messages:send"


class OperationStatus(StrEnum):
    """Stable lifecycle states for externally visible operations."""

    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    UNCERTAIN = "uncertain"


class ContractError(ValueError):
    """Report an invalid domain contract without transport-specific details."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require_identifier(value: str, field_name: str) -> None:
    if not value or value.isspace():
        raise ContractError(
            ErrorCode.INVALID_IDENTIFIER,
            f"{field_name} must be a non-blank identifier",
        )


@dataclass(frozen=True, slots=True)
class BotAddress:
    """Select one connected bot deterministically."""

    platform_id: str
    adapter_id: str
    protocol_id: str
    bot_id: str

    def __post_init__(self) -> None:
        for field_name in ("platform_id", "adapter_id", "protocol_id", "bot_id"):
            _require_identifier(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ConversationAddress:
    """Identify one conversation within a platform."""

    conversation_type: str
    conversation_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.conversation_type, "conversation_type")
        _require_identifier(self.conversation_id, "conversation_id")


@dataclass(frozen=True, slots=True)
class ServicePrincipal:
    """An external application identity, never a platform user."""

    principal_id: str
    display_name: str
    enabled: bool

    def __post_init__(self) -> None:
        _require_identifier(self.principal_id, "principal_id")
        _require_identifier(self.display_name, "display_name")


@dataclass(frozen=True, slots=True)
class ResourceGrant:
    """Bind one Service Principal to one exact messaging resource."""

    grant_id: str
    principal_id: str
    bot: BotAddress
    conversation: ConversationAddress
    revision: int

    def __post_init__(self) -> None:
        _require_identifier(self.grant_id, "grant_id")
        _require_identifier(self.principal_id, "principal_id")
        if self.revision < 1:
            raise ContractError(
                ErrorCode.INVALID_IDENTIFIER,
                "grant revision must be positive",
            )


@dataclass(frozen=True, slots=True)
class ConnectedBotSummary:
    """Privacy-bounded status for an exact connected bot."""

    address: BotAddress
    display_name: str
    connected: bool

    def __post_init__(self) -> None:
        _require_identifier(self.display_name, "display_name")


@dataclass(frozen=True, slots=True)
class TextSegment:
    """An ordered text element in an outbound message."""

    text: str

    def __post_init__(self) -> None:
        if not self.text:
            raise ContractError(
                ErrorCode.INVALID_MESSAGE_SEGMENT,
                "text segments must not be empty",
            )


@dataclass(frozen=True, slots=True)
class ImageSegment:
    """An ordered public image reference in an outbound message."""

    url: str

    def __post_init__(self) -> None:
        if not self.url:
            raise ContractError(
                ErrorCode.INVALID_MESSAGE_SEGMENT,
                "image segment URLs must not be empty",
            )


type MessageSegment = TextSegment | ImageSegment


def _freeze_segments(
    segments: tuple[MessageSegment, ...],
) -> tuple[MessageSegment, ...]:
    snapshot = tuple(segments)
    if any(type(segment) not in (TextSegment, ImageSegment) for segment in snapshot):
        raise ContractError(
            ErrorCode.INVALID_MESSAGE_SEGMENT,
            "messages only accept text and image segments",
        )
    return snapshot


@dataclass(frozen=True, slots=True)
class MessageEnvelope:
    """Normalized stored message exposed across the external boundary."""

    record_id: str
    message_id: str | None
    received_at: datetime
    bot: BotAddress
    conversation: ConversationAddress
    sender_id: str | None
    segments: tuple[MessageSegment, ...]
    processing_status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "segments", _freeze_segments(self.segments))
        _require_identifier(self.record_id, "record_id")
        if self.message_id is not None:
            _require_identifier(self.message_id, "message_id")
        if self.sender_id is not None:
            _require_identifier(self.sender_id, "sender_id")
        _require_identifier(self.processing_status, "processing_status")


@dataclass(frozen=True, slots=True)
class MessageCursor:
    """Opaque continuation token with no transferable authority."""

    value: str

    def __post_init__(self) -> None:
        _require_identifier(self.value, "cursor")


@dataclass(frozen=True, slots=True)
class ListRecentMessagesRequest:
    """Request one bounded page from one exact conversation."""

    bot: BotAddress
    conversation: ConversationAddress
    limit: int = 100
    cursor: MessageCursor | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= MAX_MESSAGE_PAGE_SIZE:
            raise ContractError(
                ErrorCode.INVALID_LIMIT,
                "message page limit must be between 1 and 200",
            )


@dataclass(frozen=True, slots=True)
class ListRecentMessagesResult:
    """One privacy-bounded page and its continuation token."""

    messages: tuple[MessageEnvelope, ...]
    next_cursor: MessageCursor | None


@dataclass(frozen=True, slots=True)
class SendMessageRequest:
    """Request one atomic, ordered platform message send."""

    bot: BotAddress
    conversation: ConversationAddress
    segments: tuple[MessageSegment, ...]
    idempotency_key: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "segments", _freeze_segments(self.segments))
        if not self.segments:
            raise ContractError(ErrorCode.EMPTY_MESSAGE, "messages need a segment")
        _require_identifier(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True, slots=True)
class SendMessageResult:
    """Stable result of an idempotent send operation."""

    operation_id: str
    status: OperationStatus
    platform_message_id: str | None = None
    error_code: ErrorCode | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.operation_id, "operation_id")
        if self.platform_message_id is not None:
            _require_identifier(self.platform_message_id, "platform_message_id")


class MessageQuery(Protocol):
    """Read normalized messages through a project-owned boundary."""

    async def list_recent(
        self,
        request: ListRecentMessagesRequest,
    ) -> ListRecentMessagesResult: ...


class MessageAction(Protocol):
    """Execute outbound messaging through a project-owned boundary."""

    async def send_message(self, request: SendMessageRequest) -> SendMessageResult: ...


class MessageProvider(Protocol):
    """Implement platform behavior without leaking SDK types upstream."""

    async def send_message(self, request: SendMessageRequest) -> SendMessageResult: ...
