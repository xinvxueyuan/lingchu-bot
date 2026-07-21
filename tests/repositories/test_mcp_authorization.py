from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models.mcp_authorization import (
    MCPResourceGrant,
    MCPServicePrincipal,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import (
    mcp_authorization as repo,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.administration import (
    CreateResourceGrantRequest,
    CreateServicePrincipalRequest,
    OAuthIdentityKind,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ContractError,
    ConversationAddress,
)

if TYPE_CHECKING:
    from unittest.mock import Mock


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for MCP authorization repository tests."""
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    return session


def _principal(*, enabled: bool = True) -> MagicMock:
    item = MagicMock(spec=MCPServicePrincipal)
    item.principal_id = "principal-1"
    item.issuer = "https://issuer.example"
    item.identity_kind = "subject"
    item.identity_value = "client-1"
    item.display_name = "Client One"
    item.enabled = enabled
    return item


def _grant(*, revision: int = 1, revoked: bool = False) -> MagicMock:
    item = MagicMock(spec=MCPResourceGrant)
    item.grant_id = "grant-1"
    item.principal_id = "principal-1"
    item.platform_id = "qq"
    item.adapter_id = "onebot.v11"
    item.protocol_id = "onebot.v11"
    item.bot_id = "10001"
    item.conversation_type = "group"
    item.conversation_id = "20002"
    item.revision = revision
    item.revoked_at = MagicMock() if revoked else None
    return item


def _grant_request() -> CreateResourceGrantRequest:
    return CreateResourceGrantRequest(
        grant_id="grant-1",
        principal_id="principal-1",
        bot=BotAddress("qq", "onebot.v11", "onebot.v11", "10001"),
        conversation=ConversationAddress("group", "20002"),
    )


@pytest.mark.asyncio
async def test_create_principal_enforces_issuer_subject_identity(
    mock_session: Mock,
) -> None:
    request = CreateServicePrincipalRequest(
        principal_id="principal-1",
        issuer="https://issuer.example",
        identity_kind=OAuthIdentityKind.SUBJECT,
        identity_value="client-1",
        display_name="Client One",
    )
    existing = _principal()
    get_mock = AsyncMock(return_value=existing)
    create_mock = AsyncMock()
    with (
        patch.object(repo, "get_one", get_mock),
        patch.object(repo, "create", create_mock),
    ):
        result = await repo.create_service_principal(mock_session, request)
    assert result.principal_id == "principal-1"
    assert get_mock.call_args.args[0] is mock_session
    assert get_mock.call_args.args[2] == {
        "issuer": "https://issuer.example",
        "identity_kind": "subject",
        "identity_value": "client-1",
    }
    create_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_principal_preserves_disabled_state(mock_session: Mock) -> None:
    get_mock = AsyncMock(return_value=_principal(enabled=False))
    with patch.object(repo, "get_one", get_mock):
        result = await repo.resolve_service_principal(
            mock_session,
            issuer="https://issuer.example",
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="client-1",
        )
    assert result is not None
    assert result.enabled is False


def test_principal_rejects_invalid_identity_kind() -> None:
    with pytest.raises(ContractError):
        CreateServicePrincipalRequest(
            principal_id="principal-1",
            issuer="https://issuer.example",
            identity_kind=cast("OAuthIdentityKind", "implicit"),
            identity_value="client-1",
            display_name="Client One",
        )


@pytest.mark.asyncio
async def test_same_issuer_and_value_use_separate_identity_kind_namespaces(
    mock_session: Mock,
) -> None:
    get_mock = AsyncMock(side_effect=[_principal(), None])
    created = _principal()
    created.identity_kind = "client_id"
    create_mock = AsyncMock(return_value=created)
    with (
        patch.object(repo, "get_one", get_mock),
        patch.object(repo, "create", create_mock),
    ):
        subject = await repo.resolve_service_principal(
            mock_session,
            issuer="https://issuer.example",
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="client-1",
        )
        client = await repo.create_service_principal(
            mock_session,
            CreateServicePrincipalRequest(
                principal_id="principal-2",
                issuer="https://issuer.example",
                identity_kind=OAuthIdentityKind.CLIENT_ID,
                identity_value="client-1",
                display_name="Client Credential",
            ),
        )
    assert subject is not None
    assert client.principal_id == "principal-1"
    assert create_mock.call_args.kwargs["identity_kind"] == "client_id"


@pytest.mark.parametrize("value", ["", " ", "*"])
def test_grant_rejects_blank_or_wildcard_resource(value: str) -> None:
    with pytest.raises(ContractError):
        CreateResourceGrantRequest(
            grant_id="grant-1",
            principal_id="principal-1",
            bot=BotAddress("qq", "onebot.v11", "onebot.v11", "10001"),
            conversation=ConversationAddress("group", value),
        )


@pytest.mark.asyncio
async def test_find_grant_requires_every_exact_resource_component(
    mock_session: Mock,
) -> None:
    get_mock = AsyncMock(return_value=_grant())
    request = _grant_request()
    with patch.object(repo, "get_one", get_mock):
        result = await repo.find_exact_resource_grant(
            mock_session,
            principal_id=request.principal_id,
            bot=request.bot,
            conversation=request.conversation,
        )
    assert result is not None
    assert get_mock.call_args.args[0] is mock_session
    assert get_mock.call_args.args[2] == {
        "principal_id": "principal-1",
        "platform_id": "qq",
        "adapter_id": "onebot.v11",
        "protocol_id": "onebot.v11",
        "bot_id": "10001",
        "conversation_type": "group",
        "conversation_id": "20002",
        "revoked_at": None,
    }


@pytest.mark.asyncio
async def test_has_any_active_grant_uses_principal_and_active_predicate(
    mock_session: Mock,
) -> None:
    exists_mock = AsyncMock(return_value=True)
    with patch.object(repo, "exists", exists_mock):
        result = await repo.has_any_active_grant(
            mock_session, principal_id="principal-1"
        )
    assert result is True
    assert exists_mock.call_args.args == (
        mock_session,
        MCPResourceGrant,
        {"principal_id": "principal-1", "revoked_at": None},
    )


@pytest.mark.asyncio
async def test_list_active_grants_is_stable_and_session_first(
    mock_session: Mock,
) -> None:
    list_mock = AsyncMock(return_value=[_grant()])
    with patch.object(repo, "list_items", list_mock):
        grants = await repo.list_active_resource_grants(
            mock_session,
            principal_id="principal-1",
        )

    assert len(grants) == 1
    assert grants[0].grant_id == "grant-1"
    list_mock.assert_awaited_once_with(
        mock_session,
        MCPResourceGrant,
        {"principal_id": "principal-1", "revoked_at": None},
        order_by=["grant_id"],
    )


@pytest.mark.asyncio
async def test_regrant_revoked_resource_increments_revision(mock_session: Mock) -> None:
    existing = _grant(revision=4, revoked=True)
    updated = _grant(revision=5)
    get_mock = AsyncMock(side_effect=[existing, updated])
    update_mock = AsyncMock(return_value=(1, True))
    with (
        patch.object(repo, "get_one", get_mock),
        patch.object(repo, "update", update_mock),
    ):
        result = await repo.create_resource_grant(mock_session, _grant_request())
    assert result.revision == 5
    assert update_mock.call_args.args[3]["revision"] == 5
    assert update_mock.call_args.args[3]["revoked_at"] is None


@pytest.mark.asyncio
async def test_revocation_increments_revision_and_invalidates_match(
    mock_session: Mock,
) -> None:
    active = _grant(revision=2)
    get_mock = AsyncMock(side_effect=[active, None])
    update_mock = AsyncMock(return_value=(1, True))
    with (
        patch.object(repo, "get_one", get_mock),
        patch.object(repo, "update", update_mock),
    ):
        result = await repo.revoke_resource_grant(mock_session, "grant-1")
    assert result is True
    assert update_mock.call_args.args[3]["revision"] == 3
    assert update_mock.call_args.args[3]["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revocation_retries_when_revision_compare_and_swap_loses(
    mock_session: Mock,
) -> None:
    first = _grant(revision=2)
    concurrent = _grant(revision=3)
    get_mock = AsyncMock(side_effect=[first, concurrent])
    update_mock = AsyncMock(side_effect=[(0, True), (1, True)])
    with (
        patch.object(repo, "get_one", get_mock),
        patch.object(repo, "update", update_mock),
    ):
        assert await repo.revoke_resource_grant(mock_session, "grant-1") is True
    assert update_mock.call_args_list[0].args[2]["revision"] == 2
    assert update_mock.call_args_list[1].args[2]["revision"] == 3


@pytest.mark.asyncio
async def test_revocation_unknown_rowcount_never_assumes_success(
    mock_session: Mock,
) -> None:
    unchanged = _grant(revision=2)
    get_mock = AsyncMock(return_value=unchanged)
    update_mock = AsyncMock(return_value=(-1, False))
    with (
        patch.object(repo, "get_one", get_mock),
        patch.object(repo, "update", update_mock),
    ):
        assert await repo.revoke_resource_grant(mock_session, "grant-1") is False
    assert update_mock.await_count == 3


@pytest.mark.asyncio
async def test_regrant_unknown_rowcount_requires_matching_revision_and_state(
    mock_session: Mock,
) -> None:
    revoked = _grant(revision=4, revoked=True)
    get_mock = AsyncMock(return_value=revoked)
    update_mock = AsyncMock(return_value=(-1, False))
    with (
        patch.object(repo, "get_one", get_mock),
        patch.object(repo, "update", update_mock),
        pytest.raises(RuntimeError),
    ):
        await repo.create_resource_grant(mock_session, _grant_request())
    assert update_mock.await_count == 3
