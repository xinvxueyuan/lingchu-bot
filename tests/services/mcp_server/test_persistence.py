from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.administration import (
    OAuthIdentityKind,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.auth import (
    AuthenticatedPrincipal,
    ResourceAuthorization,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.authorized_message_query import (
    SensitiveReadAuditError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    CapabilityScope,
    ConversationAddress,
    OperationStatus,
    ResourceGrant,
    SendMessageResult,
    ServicePrincipal,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.persistence import (
    MCPServerAudit,
    ScopedAuthorizationRepository,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

SESSION = MagicMock()
BOT = BotAddress("qq", "~onebot.v11", "default", "10001")
CONVERSATION = ConversationAddress("group", "20002")
PRINCIPAL = ServicePrincipal("principal-1", "Client One", enabled=True)
AUTHENTICATED = AuthenticatedPrincipal(
    PRINCIPAL,
    "https://issuer.example",
    OAuthIdentityKind.SUBJECT,
    "subject-1",
    frozenset({"messages:read", "messages:send"}),
    2**63 - 1,
    None,
)
GRANT = ResourceGrant("grant-1", "principal-1", BOT, CONVERSATION, 1)
AUTHORIZATION = ResourceAuthorization(
    AUTHENTICATED, CapabilityScope.MESSAGES_READ, GRANT
)


@asynccontextmanager
async def session_factory() -> AsyncGenerator[AsyncSession]:
    yield SESSION


@pytest.mark.asyncio
async def test_scoped_authorization_repository_passes_session_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve = AsyncMock(return_value=PRINCIPAL)
    find = AsyncMock(return_value=GRANT)
    any_grant = AsyncMock(return_value=True)
    list_grants = AsyncMock(return_value=(GRANT,))
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.persistence.mcp_authorization.resolve_service_principal",
        resolve,
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.persistence.mcp_authorization.find_exact_resource_grant",
        find,
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.persistence.mcp_authorization.has_any_active_grant",
        any_grant,
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.persistence."
        "mcp_authorization.list_active_resource_grants",
        list_grants,
    )
    repository = ScopedAuthorizationRepository(session_factory)
    assert (
        await repository.resolve_principal(
            issuer="https://issuer.example",
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="subject-1",
        )
        is PRINCIPAL
    )
    assert (
        await repository.find_exact_grant(
            principal_id="principal-1", bot=BOT, conversation=CONVERSATION
        )
        is GRANT
    )
    assert await repository.has_any_active_grant(principal_id="principal-1")
    assert await repository.list_active_grants(principal_id="principal-1") == (GRANT,)
    assert resolve.call_args.args[0] is SESSION
    assert find.call_args.args[0] is SESSION
    assert any_grant.call_args.args[0] is SESSION
    assert list_grants.call_args.args[0] is SESSION


@pytest.mark.asyncio
async def test_pre_read_audit_is_durable_and_privacy_bounded() -> None:
    writer = AsyncMock(return_value=object())
    audit = MCPServerAudit(session_factory, writer)
    await audit.record_pre_read(AUTHORIZATION)
    event = writer.call_args.args[1]
    assert writer.call_args.args[0] is SESSION
    assert event.api_name == "mcp.messages.list_recent"
    assert event.audit_type == "mcp_server"
    assert "principal-1" in (event.data_summary or "")
    assert "subject-1" not in (event.data_summary or "")


@pytest.mark.asyncio
async def test_pre_read_audit_fails_closed() -> None:
    audit = MCPServerAudit(session_factory, AsyncMock(side_effect=OSError))
    with pytest.raises(SensitiveReadAuditError):
        await audit.record_pre_read(AUTHORIZATION)


@pytest.mark.asyncio
async def test_send_audit_records_pre_and_post_states() -> None:
    writer = AsyncMock(return_value=object())
    audit = MCPServerAudit(session_factory, writer)
    payload: dict[str, object] = {
        "operation_id": "operation-1",
        "principal_id": "principal-1",
    }
    await audit.record_pre_send(AUTHORIZATION, payload)
    await audit.record_post_send(
        AUTHORIZATION,
        payload,
        SendMessageResult("operation-1", OperationStatus.SUCCEEDED, "message-1"),
    )
    assert writer.await_count == 2
    pre_event = writer.call_args_list[0].args[1]
    post_event = writer.call_args_list[1].args[1]
    assert pre_event.result_summary == "pre_send"
    assert "succeeded" in (post_event.result_summary or "")
