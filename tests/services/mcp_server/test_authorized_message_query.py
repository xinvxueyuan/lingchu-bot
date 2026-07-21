from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.administration import (
    OAuthIdentityKind,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.auth import (
    AuthenticatedPrincipal,
    AuthorizationError,
    ResourceAuthorization,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.authorized_message_query import (
    AuthorizedMessageQuery,
    MessagePage,
    MessagePageRequest,
    SensitiveReadAuditError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    CapabilityScope,
    ContractError,
    ConversationAddress,
    ErrorCode,
    ListRecentMessagesRequest,
    MessageEnvelope,
    ResourceGrant,
    ServicePrincipal,
    TextSegment,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.cursor import (
    CursorCodec,
    CursorPosition,
)

NOW = datetime(2026, 7, 18, 8, tzinfo=UTC)
BOT = BotAddress("qq", "~onebot.v11", "napcat", "bot-1")
CONVERSATION = ConversationAddress("group", "group-1")
PRINCIPAL = ServicePrincipal("principal-1", "Worker", enabled=True)
AUTHENTICATED = AuthenticatedPrincipal(
    PRINCIPAL,
    "https://issuer.example",
    identity_kind=OAuthIdentityKind.SUBJECT,
    identity_value="worker",
    scopes=frozenset({CapabilityScope.MESSAGES_READ.value}),
    expires_at=2_000_000_000,
    not_before=None,
)
GRANT = ResourceGrant("grant-1", "principal-1", BOT, CONVERSATION, 3)


def _message(record_id: str, minute: int) -> MessageEnvelope:
    return MessageEnvelope(
        record_id,
        f"message-{record_id}",
        datetime(2026, 7, 18, 7, minute, tzinfo=UTC),
        BOT,
        CONVERSATION,
        "sender-1",
        (TextSegment(record_id),),
        "processed",
    )


class FakePolicy:
    def __init__(
        self, grant: ResourceGrant = GRANT, *, revoke_before_read: bool = False
    ) -> None:
        self.grant = grant
        self.revoke_before_read = revoke_before_read
        self.calls = 0
        self.rechecks = 0

    async def authorize_resource(
        self, *args: object, **kwargs: object
    ) -> ResourceAuthorization:
        self.calls += 1
        return ResourceAuthorization(
            AUTHENTICATED, CapabilityScope.MESSAGES_READ, self.grant
        )

    async def recheck(
        self, authorization: ResourceAuthorization
    ) -> ResourceAuthorization:
        self.rechecks += 1
        if self.revoke_before_read:
            raise AuthorizationError
        return authorization


class FakeSource:
    def __init__(self, pages: list[MessagePage]) -> None:
        self.pages = pages
        self.requests: list[MessagePageRequest] = []

    async def list_page(self, request: MessagePageRequest) -> MessagePage:
        self.requests.append(request)
        return self.pages.pop(0)


class FakeAudit:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails
        self.authorizations: list[ResourceAuthorization] = []

    async def record_pre_read(self, authorization: ResourceAuthorization) -> None:
        self.authorizations.append(authorization)
        if self.fails:
            raise SensitiveReadAuditError


def _service(
    source: FakeSource,
    audit: FakeAudit | None = None,
    policy: FakePolicy | None = None,
) -> AuthorizedMessageQuery:
    return AuthorizedMessageQuery(
        policy=policy or FakePolicy(),
        source=source,
        cursor_codec=CursorCodec(
            secret=b"0123456789abcdef0123456789abcdef", clock=lambda: NOW
        ),
        audit=audit or FakeAudit(),
    )


@pytest.mark.asyncio
async def test_list_recent_freezes_window_and_continues_in_stable_order() -> None:
    newest, middle, oldest = _message("30", 30), _message("20", 20), _message("10", 10)
    source = FakeSource([
        MessagePage((newest, middle, oldest), anchor_exists=True),
        MessagePage((oldest,), anchor_exists=True),
    ])
    service = _service(source)
    request = ListRecentMessagesRequest(BOT, CONVERSATION, limit=2)

    first = await service.list_recent(AUTHENTICATED, request)
    second = await service.list_recent(
        AUTHENTICATED,
        ListRecentMessagesRequest(BOT, CONVERSATION, limit=2, cursor=first.next_cursor),
    )

    assert first.messages == (newest, middle)
    assert first.next_cursor is not None
    assert second.messages == (oldest,)
    assert second.next_cursor is None
    assert source.requests[0] == MessagePageRequest(BOT, CONVERSATION, 3, None, None)
    assert source.requests[1] == MessagePageRequest(
        BOT,
        CONVERSATION,
        3,
        CursorPosition(middle.received_at, middle.record_id),
        CursorPosition(newest.received_at, newest.record_id),
    )


@pytest.mark.asyncio
async def test_list_recent_reports_retention_gap_as_cursor_expired() -> None:
    newest, older = _message("30", 30), _message("20", 20)
    source = FakeSource([
        MessagePage((newest, older), anchor_exists=True),
        MessagePage((), anchor_exists=False),
    ])
    service = _service(source)
    first = await service.list_recent(
        AUTHENTICATED, ListRecentMessagesRequest(BOT, CONVERSATION, limit=1)
    )

    with pytest.raises(ContractError) as caught:
        await service.list_recent(
            AUTHENTICATED,
            ListRecentMessagesRequest(
                BOT, CONVERSATION, limit=1, cursor=first.next_cursor
            ),
        )

    assert caught.value.code is ErrorCode.CURSOR_EXPIRED


@pytest.mark.asyncio
async def test_list_recent_rejects_changed_limit_bound_to_cursor() -> None:
    source = FakeSource([
        MessagePage((_message("30", 30), _message("20", 20)), anchor_exists=True)
    ])
    service = _service(source)
    first = await service.list_recent(
        AUTHENTICATED, ListRecentMessagesRequest(BOT, CONVERSATION, limit=1)
    )

    with pytest.raises(ContractError) as caught:
        await service.list_recent(
            AUTHENTICATED,
            ListRecentMessagesRequest(
                BOT, CONVERSATION, limit=2, cursor=first.next_cursor
            ),
        )

    assert caught.value.code is ErrorCode.INVALID_CURSOR


@pytest.mark.asyncio
async def test_sensitive_read_audit_failure_prevents_message_access() -> None:
    source = FakeSource([MessagePage((_message("30", 30),), anchor_exists=True)])
    audit = FakeAudit(fails=True)
    service = _service(source, audit)

    with pytest.raises(ContractError) as caught:
        await service.list_recent(
            AUTHENTICATED, ListRecentMessagesRequest(BOT, CONVERSATION, limit=200)
        )

    assert caught.value.code is ErrorCode.AUDIT_UNAVAILABLE
    assert source.requests == []
    assert audit.authorizations[0].grant == GRANT


@pytest.mark.asyncio
async def test_grant_revocation_after_audit_prevents_message_access() -> None:
    source = FakeSource([MessagePage((_message("30", 30),), anchor_exists=True)])
    policy = FakePolicy(revoke_before_read=True)
    service = _service(source, policy=policy)

    with pytest.raises(AuthorizationError):
        await service.list_recent(
            AUTHENTICATED, ListRecentMessagesRequest(BOT, CONVERSATION, limit=1)
        )

    assert policy.calls == 1
    assert policy.rechecks == 1
    assert source.requests == []
