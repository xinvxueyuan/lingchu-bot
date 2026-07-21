from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.administration import (
    OAuthIdentityKind,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.auth import (
    AuthenticationError,
    AuthorizationError,
    AuthorizationPolicy,
    CatalogEntry,
    OAuthIssuerPolicy,
    ProjectTokenVerifier,
    SignedTokenVerificationError,
    TokenClaims,
    filter_catalog,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    CapabilityScope,
    ConversationAddress,
    ResourceGrant,
    ServicePrincipal,
)

ISSUER = "https://identity.example.com"
AUDIENCE = "https://bot.example.com/mcp"
TOKEN = "header.payload.signature"
BOT = BotAddress("qq", "onebot-v11", "onebot-v11", "10001")
CONVERSATION = ConversationAddress("group", "20002")


class FakeDecoder:
    def __init__(self, claims: dict[str, Any] | None = None) -> None:
        now = int(time())
        self.claims = claims or {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": "automation-service",
            "client_id": "oauth-client",
            "scope": "bots:list messages:read messages:send superuser",
            "exp": now + 300,
            "nbf": now - 1,
        }
        self.signature_valid = True

    async def decode_and_verify(self, token: str) -> dict[str, Any]:
        assert token == TOKEN
        if not self.signature_valid:
            raise SignedTokenVerificationError(
                "signature failed for secret token material"
            )
        return self.claims


@dataclass
class FakeRepository:
    principal: ServicePrincipal | None = field(
        default_factory=lambda: ServicePrincipal(
            "principal-1", "Automation", enabled=True
        )
    )
    grant: ResourceGrant | None = field(
        default_factory=lambda: ResourceGrant(
            "grant-1", "principal-1", BOT, CONVERSATION, 1
        )
    )
    has_active_grant: bool = True

    async def resolve_principal(
        self,
        *,
        issuer: str,
        identity_kind: OAuthIdentityKind,
        identity_value: str,
    ) -> ServicePrincipal | None:
        assert issuer == ISSUER
        assert identity_kind is OAuthIdentityKind.SUBJECT
        assert identity_value == "automation-service"
        return self.principal

    async def find_exact_grant(
        self,
        *,
        principal_id: str,
        bot: BotAddress,
        conversation: ConversationAddress,
    ) -> ResourceGrant | None:
        assert principal_id == "principal-1"
        assert bot == BOT
        assert conversation == CONVERSATION
        return self.grant

    async def has_any_active_grant(self, *, principal_id: str) -> bool:
        assert principal_id == "principal-1"
        return self.has_active_grant


def verifier(decoder: FakeDecoder) -> ProjectTokenVerifier:
    return ProjectTokenVerifier(
        decoder=decoder,
        issuer_policy=OAuthIssuerPolicy(
            issuer=ISSUER,
            audience=AUDIENCE,
            identity_kind=OAuthIdentityKind.SUBJECT,
        ),
    )


@pytest.mark.asyncio
async def test_verifier_returns_sdk_access_token_for_valid_claims() -> None:
    access_token = await verifier(FakeDecoder()).verify_token(TOKEN)

    assert access_token is not None
    assert access_token.subject == "automation-service"
    assert access_token.client_id == "oauth-client"
    assert access_token.scopes == [
        "bots:list",
        "messages:read",
        "messages:send",
        "superuser",
    ]
    assert access_token.resource == AUDIENCE


@pytest.mark.asyncio
@pytest.mark.parametrize("numeric_date", [True, float("nan"), float("inf"), -1, 2**80])
async def test_verifier_rejects_hostile_numeric_dates(numeric_date: object) -> None:
    decoder = FakeDecoder()
    decoder.claims["exp"] = numeric_date

    assert await verifier(decoder).verify_token(TOKEN) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("iss", "https://attacker.example.com"),
        ("aud", "https://other.example.com/mcp"),
        ("exp", 1),
        pytest.param("nbf", int(time()) + 300, id="nbf-future"),
    ],
)
async def test_verifier_rejects_invalid_security_claims(
    claim: str, value: object
) -> None:
    decoder = FakeDecoder()
    decoder.claims[claim] = value

    assert await verifier(decoder).verify_token(TOKEN) is None


@pytest.mark.asyncio
async def test_verifier_rejects_invalid_signature_without_leaking_details() -> None:
    decoder = FakeDecoder()
    decoder.signature_valid = False

    assert await verifier(decoder).verify_token(TOKEN) is None


@pytest.mark.asyncio
async def test_verifier_does_not_fallback_between_identity_claims() -> None:
    decoder = FakeDecoder()
    decoder.claims.pop("sub")

    assert await verifier(decoder).verify_token(TOKEN) is None


@pytest.mark.asyncio
async def test_client_identity_policy_uses_client_id_even_when_subject_exists() -> None:
    decoder = FakeDecoder()
    client_verifier = ProjectTokenVerifier(
        decoder=decoder,
        issuer_policy=OAuthIssuerPolicy(
            issuer=ISSUER,
            audience=AUDIENCE,
            identity_kind=OAuthIdentityKind.CLIENT_ID,
        ),
    )

    claims = await client_verifier.verify_claims(TOKEN)

    assert claims.identity_kind is OAuthIdentityKind.CLIENT_ID
    assert claims.identity_value == "oauth-client"


@pytest.mark.asyncio
async def test_authentication_resolves_only_configured_claim_namespace() -> None:
    claims = TokenClaims(
        issuer=ISSUER,
        identity_kind=OAuthIdentityKind.SUBJECT,
        identity_value="automation-service",
        client_id="oauth-client",
        scopes=frozenset({CapabilityScope.MESSAGES_READ.value}),
        expires_at=int(time()) + 300,
    )

    authenticated = await AuthorizationPolicy(FakeRepository()).authenticate(claims)

    assert authenticated.principal.principal_id == "principal-1"
    assert authenticated.scopes == frozenset({"messages:read"})


@pytest.mark.asyncio
async def test_authentication_rejects_disabled_principal() -> None:
    repository = FakeRepository(
        principal=ServicePrincipal("principal-1", "Automation", enabled=False)
    )
    claims = TokenClaims(
        issuer=ISSUER,
        identity_kind=OAuthIdentityKind.SUBJECT,
        identity_value="automation-service",
        client_id="oauth-client",
        scopes=frozenset({"messages:read"}),
        expires_at=int(time()) + 300,
    )

    with pytest.raises(AuthenticationError, match="authentication failed"):
        await AuthorizationPolicy(repository).authenticate(claims)


@pytest.mark.asyncio
async def test_authorization_requires_scope_and_exact_resource_grant() -> None:
    policy = AuthorizationPolicy(FakeRepository())
    authenticated = await policy.authenticate(
        TokenClaims(
            issuer=ISSUER,
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="automation-service",
            client_id="oauth-client",
            scopes=frozenset({"messages:read", "superuser"}),
            expires_at=int(time()) + 300,
        )
    )

    decision = await policy.authorize_resource(
        authenticated,
        capability=CapabilityScope.MESSAGES_READ,
        bot=BOT,
        conversation=CONVERSATION,
    )

    assert decision.grant.grant_id == "grant-1"

    with pytest.raises(AuthorizationError, match="authorization denied"):
        await policy.authorize_resource(
            authenticated,
            capability=CapabilityScope.MESSAGES_SEND,
            bot=BOT,
            conversation=CONVERSATION,
        )


@pytest.mark.asyncio
async def test_superuser_scope_does_not_bypass_revoked_grant() -> None:
    repository = FakeRepository(grant=None)
    policy = AuthorizationPolicy(repository)
    authenticated = await policy.authenticate(
        TokenClaims(
            issuer=ISSUER,
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="automation-service",
            client_id="oauth-client",
            scopes=frozenset({"messages:read", "superuser"}),
            expires_at=int(time()) + 300,
        )
    )

    with pytest.raises(AuthorizationError, match="authorization denied"):
        await policy.authorize_resource(
            authenticated,
            capability=CapabilityScope.MESSAGES_READ,
            bot=BOT,
            conversation=CONVERSATION,
        )


@pytest.mark.asyncio
async def test_recheck_rejects_principal_or_grant_changed_after_decision() -> None:
    repository = FakeRepository()
    policy = AuthorizationPolicy(repository)
    authenticated = await policy.authenticate(
        TokenClaims(
            issuer=ISSUER,
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="automation-service",
            client_id="oauth-client",
            scopes=frozenset({"messages:send"}),
            expires_at=int(time()) + 300,
        )
    )
    decision = await policy.authorize_resource(
        authenticated,
        capability=CapabilityScope.MESSAGES_SEND,
        bot=BOT,
        conversation=CONVERSATION,
    )

    repository.grant = ResourceGrant("grant-1", "principal-1", BOT, CONVERSATION, 2)
    with pytest.raises(AuthorizationError, match="authorization denied"):
        await policy.recheck(decision)

    repository.grant = decision.grant
    repository.principal = ServicePrincipal("principal-1", "Automation", enabled=False)
    with pytest.raises(AuthorizationError, match="authorization denied"):
        await policy.recheck(decision)


@pytest.mark.asyncio
async def test_recheck_rejects_token_that_expired_after_initial_decision() -> None:
    now = 1_000
    repository = FakeRepository()
    policy = AuthorizationPolicy(repository, clock=lambda: now)
    authenticated = await policy.authenticate(
        TokenClaims(
            issuer=ISSUER,
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="automation-service",
            client_id="oauth-client",
            scopes=frozenset({"messages:send"}),
            expires_at=now + 1,
            not_before=now - 1,
        )
    )
    decision = await policy.authorize_resource(
        authenticated,
        capability=CapabilityScope.MESSAGES_SEND,
        bot=BOT,
        conversation=CONVERSATION,
    )
    now += 2

    with pytest.raises(AuthorizationError, match="authorization denied"):
        await policy.recheck(decision)


@pytest.mark.asyncio
async def test_recheck_preserves_and_enforces_not_before() -> None:
    now = 1_000
    repository = FakeRepository()
    policy = AuthorizationPolicy(repository, clock=lambda: now)
    authenticated = await policy.authenticate(
        TokenClaims(
            issuer=ISSUER,
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="automation-service",
            client_id="oauth-client",
            scopes=frozenset({"messages:send"}),
            expires_at=now + 300,
            not_before=now,
        )
    )
    decision = await policy.authorize_resource(
        authenticated,
        capability=CapabilityScope.MESSAGES_SEND,
        bot=BOT,
        conversation=CONVERSATION,
    )
    now -= 1

    with pytest.raises(AuthorizationError, match="authorization denied"):
        await policy.recheck(decision)


@pytest.mark.asyncio
async def test_catalog_requires_current_principal_scope_and_grant_policy() -> None:
    catalog = (
        CatalogEntry("bots.list", CapabilityScope.BOTS_LIST, resource_bound=False),
        CatalogEntry(
            "messages.list_recent", CapabilityScope.MESSAGES_READ, resource_bound=True
        ),
        CatalogEntry(
            "messages.send", CapabilityScope.MESSAGES_SEND, resource_bound=True
        ),
    )
    repository = FakeRepository()
    policy = AuthorizationPolicy(repository)
    authenticated = await policy.authenticate(
        TokenClaims(
            issuer=ISSUER,
            identity_kind=OAuthIdentityKind.SUBJECT,
            identity_value="automation-service",
            client_id="oauth-client",
            scopes=frozenset({"bots:list", "messages:read", "superuser"}),
            expires_at=int(time()) + 300,
        )
    )

    visible = await filter_catalog(policy, authenticated, catalog)

    assert visible == (catalog[0], catalog[1])

    repository.has_active_grant = False
    visible_after_revocation = await filter_catalog(policy, authenticated, catalog)

    assert visible_after_revocation == (catalog[0],)

    repository.principal = ServicePrincipal("principal-1", "Automation", enabled=False)
    visible_after_disable = await filter_catalog(policy, authenticated, catalog)

    assert visible_after_disable == ()


def test_auth_errors_never_include_token_or_hostile_claim_metadata() -> None:
    token = "secret.bearer.token"
    hostile = "\nFORGED LOG ENTRY"

    error = AuthenticationError(token, hostile)

    assert str(error) == "authentication failed"
    assert token not in repr(error)
    assert hostile not in repr(error)
