"""Authorized, audited message history pagination."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Protocol

from .contracts import (
    BotAddress,
    CapabilityScope,
    ContractError,
    ConversationAddress,
    ErrorCode,
    ListRecentMessagesRequest,
    ListRecentMessagesResult,
    MessageEnvelope,
)
from .cursor import CursorBinding, CursorCodec, CursorPosition

if TYPE_CHECKING:
    from .auth import AuthenticatedPrincipal, ResourceAuthorization

_CURSOR_EXPIRED = "message cursor expired"
_AUDIT_UNAVAILABLE = "sensitive read audit unavailable"


@dataclass(frozen=True, slots=True)
class MessagePageRequest:
    """Internal stable-window request to a privacy-bounded message source."""

    bot: BotAddress
    conversation: ConversationAddress
    limit: int
    after: CursorPosition | None
    window_end: CursorPosition | None


@dataclass(frozen=True, slots=True)
class MessagePage:
    """Bounded source page plus continuation-anchor retention status."""

    messages: tuple[MessageEnvelope, ...]
    anchor_exists: bool


class MessagePageSource(Protocol):
    """Read normalized messages in stable `(received_at, record_id)` order."""

    async def list_page(self, request: MessagePageRequest) -> MessagePage: ...


class ResourcePolicy(Protocol):
    """Authorize one exact current resource grant."""

    async def authorize_resource(
        self,
        authenticated: AuthenticatedPrincipal,
        *,
        capability: CapabilityScope,
        bot: BotAddress,
        conversation: ConversationAddress,
    ) -> ResourceAuthorization: ...

    async def recheck(
        self, authorization: ResourceAuthorization
    ) -> ResourceAuthorization: ...


class SensitiveReadAudit(Protocol):
    """Durably record authorization before a sensitive read executes."""

    async def record_pre_read(self, authorization: ResourceAuthorization) -> None: ...


class SensitiveReadAuditError(Exception):
    """Signal a durable pre-read audit failure."""


def _query_fingerprint(limit: int) -> str:
    return sha256(f"messages.list_recent\0{limit}".encode()).hexdigest()


def _position(message: MessageEnvelope) -> CursorPosition:
    return CursorPosition(message.received_at, message.record_id)


class AuthorizedMessageQuery:
    """Intersect authority, audit, cursor binding, and message pagination."""

    def __init__(
        self,
        *,
        policy: ResourcePolicy,
        source: MessagePageSource,
        cursor_codec: CursorCodec,
        audit: SensitiveReadAudit,
    ) -> None:
        self._policy = policy
        self._source = source
        self._cursor_codec = cursor_codec
        self._audit = audit

    async def list_recent(
        self,
        authenticated: AuthenticatedPrincipal,
        request: ListRecentMessagesRequest,
    ) -> ListRecentMessagesResult:
        """Return one current-authority, fail-closed audited message page."""
        authorization = await self._policy.authorize_resource(
            authenticated,
            capability=CapabilityScope.MESSAGES_READ,
            bot=request.bot,
            conversation=request.conversation,
        )
        binding = CursorBinding(
            authenticated.principal.principal_id,
            authorization.grant.grant_id,
            authorization.grant.revision,
            request.bot,
            request.conversation,
            _query_fingerprint(request.limit),
        )
        after: CursorPosition | None = None
        window_end: CursorPosition | None = None
        if request.cursor is not None:
            state = self._cursor_codec.decode(request.cursor, expected=binding)
            after = state.position
            window_end = state.window_end
        try:
            await self._audit.record_pre_read(authorization)
        except SensitiveReadAuditError:
            raise ContractError(
                ErrorCode.AUDIT_UNAVAILABLE, _AUDIT_UNAVAILABLE
            ) from None
        await self._policy.recheck(authorization)
        page = await self._source.list_page(
            MessagePageRequest(
                request.bot,
                request.conversation,
                request.limit + 1,
                after,
                window_end,
            )
        )
        if after is not None and not page.anchor_exists:
            raise ContractError(ErrorCode.CURSOR_EXPIRED, _CURSOR_EXPIRED)
        visible = page.messages[: request.limit]
        has_more = len(page.messages) > request.limit
        if not has_more or not visible:
            return ListRecentMessagesResult(visible, None)
        frozen_window = window_end or _position(page.messages[0])
        next_cursor = self._cursor_codec.encode(
            binding,
            position=_position(visible[-1]),
            window_end=frozen_window,
        )
        return ListRecentMessagesResult(visible, next_cursor)


__all__ = (
    "AuthorizedMessageQuery",
    "MessagePage",
    "MessagePageRequest",
    "MessagePageSource",
    "ResourcePolicy",
    "SensitiveReadAudit",
    "SensitiveReadAuditError",
)
