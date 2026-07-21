from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import time
from typing import TYPE_CHECKING, Any, Protocol, cast

from mcp.server.auth.provider import AccessToken

from .administration import OAuthIdentityKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from .contracts import (
        BotAddress,
        CapabilityScope,
        ConversationAddress,
        ResourceGrant,
        ServicePrincipal,
    )

_AUTHENTICATION_FAILED = "authentication failed"
_AUTHORIZATION_DENIED = "authorization denied"
_MAX_NUMERIC_DATE = 2**63 - 1


class AuthenticationError(Exception):
    """Expose one safe authentication failure without hostile metadata."""

    def __init__(self, *_sensitive_details: object) -> None:
        super().__init__(_AUTHENTICATION_FAILED)


class AuthorizationError(Exception):
    """Expose one safe authorization failure without policy details."""

    def __init__(self) -> None:
        super().__init__(_AUTHORIZATION_DENIED)


class SignedTokenVerificationError(Exception):
    """Signal that signature or trusted token decoding failed."""


class SignedTokenDecoder(Protocol):
    """Verify a token signature and return its trusted claims."""

    async def decode_and_verify(self, token: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class OAuthIssuerPolicy:
    """Bind one issuer to its resource and explicit identity claim namespace."""

    issuer: str
    audience: str
    identity_kind: OAuthIdentityKind


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Security-checked claims needed beyond the MCP SDK boundary."""

    issuer: str
    identity_kind: OAuthIdentityKind
    identity_value: str
    client_id: str
    scopes: frozenset[str]
    expires_at: int
    not_before: int | None = None


def _non_empty_string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise AuthenticationError
    return value


def _numeric_date(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise AuthenticationError
    if not isfinite(value) or not 0 <= value <= _MAX_NUMERIC_DATE:
        raise AuthenticationError
    try:
        return int(value)
    except (OverflowError, ValueError):
        raise AuthenticationError from None


def _audience_contains(value: object, audience: str) -> bool:
    if isinstance(value, str):
        return value == audience
    if isinstance(value, list):
        values = cast("list[object]", value)
        return audience in values and all(isinstance(item, str) for item in values)
    return False


def _parse_scopes(value: object) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset(value.split())
    if isinstance(value, list):
        values = cast("list[object]", value)
        if all(isinstance(item, str) for item in values):
            return frozenset(cast("list[str]", values))
    raise AuthenticationError


class ProjectTokenVerifier:
    """Adapt a cryptographic decoder to the MCP v1 ``TokenVerifier`` seam."""

    def __init__(
        self,
        *,
        decoder: SignedTokenDecoder,
        issuer_policy: OAuthIssuerPolicy,
        clock: Callable[[], float] = time,
    ) -> None:
        self._decoder = decoder
        self._issuer_policy = issuer_policy
        self._clock = clock

    async def verify_claims(self, token: str) -> TokenClaims:
        """Verify signature and all resource-server security claims."""
        try:
            claims = await self._decoder.decode_and_verify(token)
        except SignedTokenVerificationError:
            raise AuthenticationError from None
        issuer = _non_empty_string(claims.get("iss"))
        if issuer != self._issuer_policy.issuer:
            raise AuthenticationError
        if not _audience_contains(claims.get("aud"), self._issuer_policy.audience):
            raise AuthenticationError
        now = int(self._clock())
        expires_at = _numeric_date(claims.get("exp"))
        if expires_at <= now:
            raise AuthenticationError
        not_before: int | None = None
        not_before_claim = claims.get("nbf")
        if not_before_claim is not None:
            not_before = _numeric_date(not_before_claim)
            if not_before > now:
                raise AuthenticationError
        client_id = _non_empty_string(claims.get("client_id"))
        claim_name = (
            "sub"
            if self._issuer_policy.identity_kind is OAuthIdentityKind.SUBJECT
            else "client_id"
        )
        identity_value = _non_empty_string(claims.get(claim_name))
        scopes = _parse_scopes(claims.get("scope", ""))
        return TokenClaims(
            issuer=issuer,
            identity_kind=self._issuer_policy.identity_kind,
            identity_value=identity_value,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            not_before=not_before,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return the MCP v1 access-token representation or reject safely."""
        try:
            claims = await self.verify_claims(token)
        except AuthenticationError:
            return None
        subject = (
            claims.identity_value
            if claims.identity_kind is OAuthIdentityKind.SUBJECT
            else None
        )
        return AccessToken(
            token=token,
            client_id=claims.client_id,
            scopes=sorted(claims.scopes),
            expires_at=claims.expires_at,
            resource=self._issuer_policy.audience,
            subject=subject,
            claims={
                "iss": claims.issuer,
                "identity_kind": claims.identity_kind.value,
                "identity_value": claims.identity_value,
            },
        )


class AuthorizationRepository(Protocol):
    """Read current principal and exact-grant state for every decision."""

    async def resolve_principal(
        self,
        *,
        issuer: str,
        identity_kind: OAuthIdentityKind,
        identity_value: str,
    ) -> ServicePrincipal | None: ...

    async def find_exact_grant(
        self,
        *,
        principal_id: str,
        bot: BotAddress,
        conversation: ConversationAddress,
    ) -> ResourceGrant | None: ...

    async def has_any_active_grant(self, *, principal_id: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Enabled project principal intersected with token capability scopes."""

    principal: ServicePrincipal
    issuer: str
    identity_kind: OAuthIdentityKind
    identity_value: str
    scopes: frozenset[str]
    expires_at: int
    not_before: int | None


@dataclass(frozen=True, slots=True)
class ResourceAuthorization:
    """Snapshot that must be rechecked immediately before a write."""

    authenticated: AuthenticatedPrincipal
    capability: CapabilityScope
    grant: ResourceGrant


class AuthorizationPolicy:
    """Intersect token capability with an enabled principal and exact grant."""

    def __init__(
        self,
        repository: AuthorizationRepository,
        *,
        clock: Callable[[], float] = time,
    ) -> None:
        self._repository = repository
        self._clock = clock

    def _token_is_current(self, authenticated: AuthenticatedPrincipal) -> bool:
        now = int(self._clock())
        return authenticated.expires_at > now and (
            authenticated.not_before is None or authenticated.not_before <= now
        )

    async def authenticate(self, claims: TokenClaims) -> AuthenticatedPrincipal:
        """Resolve exactly the identity claim namespace configured for the issuer."""
        principal = await self._repository.resolve_principal(
            issuer=claims.issuer,
            identity_kind=claims.identity_kind,
            identity_value=claims.identity_value,
        )
        if principal is None or not principal.enabled:
            raise AuthenticationError
        authenticated = AuthenticatedPrincipal(
            principal=principal,
            issuer=claims.issuer,
            identity_kind=claims.identity_kind,
            identity_value=claims.identity_value,
            scopes=claims.scopes,
            expires_at=claims.expires_at,
            not_before=claims.not_before,
        )
        if not self._token_is_current(authenticated):
            raise AuthenticationError
        return authenticated

    async def authorize_resource(
        self,
        authenticated: AuthenticatedPrincipal,
        *,
        capability: CapabilityScope,
        bot: BotAddress,
        conversation: ConversationAddress,
    ) -> ResourceAuthorization:
        """Require both the OAuth capability scope and one exact active grant."""
        if (
            not self._token_is_current(authenticated)
            or capability.value not in authenticated.scopes
        ):
            raise AuthorizationError
        grant = await self._repository.find_exact_grant(
            principal_id=authenticated.principal.principal_id,
            bot=bot,
            conversation=conversation,
        )
        if grant is None:
            raise AuthorizationError
        return ResourceAuthorization(authenticated, capability, grant)

    async def recheck(
        self, authorization: ResourceAuthorization
    ) -> ResourceAuthorization:
        """Reject principal disablement, revocation, or grant revision changes."""
        current_principal = await self._repository.resolve_principal(
            issuer=authorization.authenticated.issuer,
            identity_kind=authorization.authenticated.identity_kind,
            identity_value=authorization.authenticated.identity_value,
        )
        if (
            not self._token_is_current(authorization.authenticated)
            or current_principal is None
            or not current_principal.enabled
            or current_principal.principal_id
            != authorization.authenticated.principal.principal_id
        ):
            raise AuthorizationError
        current_grant = await self._repository.find_exact_grant(
            principal_id=current_principal.principal_id,
            bot=authorization.grant.bot,
            conversation=authorization.grant.conversation,
        )
        if current_grant != authorization.grant:
            raise AuthorizationError
        return authorization

    async def principal_is_current(self, authenticated: AuthenticatedPrincipal) -> bool:
        """Re-read principal state for non-resource catalog decisions."""
        if not self._token_is_current(authenticated):
            return False
        current = await self._repository.resolve_principal(
            issuer=authenticated.issuer,
            identity_kind=authenticated.identity_kind,
            identity_value=authenticated.identity_value,
        )
        return (
            current is not None
            and current.enabled
            and current.principal_id == authenticated.principal.principal_id
        )

    async def has_active_resource_authority(
        self, authenticated: AuthenticatedPrincipal
    ) -> bool:
        """Check current principal state and at least one active exact grant."""
        if not await self.principal_is_current(authenticated):
            return False
        return await self._repository.has_any_active_grant(
            principal_id=authenticated.principal.principal_id
        )


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One statically defined external capability."""

    name: str
    required_scope: CapabilityScope
    resource_bound: bool


async def filter_catalog(
    policy: AuthorizationPolicy,
    authenticated: AuthenticatedPrincipal,
    catalog: tuple[CatalogEntry, ...],
) -> tuple[CatalogEntry, ...]:
    """Filter discovery through current principal, scope, and grant policy.

    ``bots.list`` is non-resource-bound at discovery time, but its eventual bot
    results must still be restricted to granted bots. Resource-bound message
    tools additionally require at least one currently active exact grant.
    """
    if not await policy.principal_is_current(authenticated):
        return ()
    has_resource_authority = await policy.has_active_resource_authority(authenticated)
    return tuple(
        entry
        for entry in catalog
        if entry.required_scope.value in authenticated.scopes
        and (not entry.resource_bound or has_resource_authority)
    )
