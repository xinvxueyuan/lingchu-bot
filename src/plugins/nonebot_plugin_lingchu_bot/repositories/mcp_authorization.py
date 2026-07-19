from __future__ import annotations

from typing import TYPE_CHECKING

from ..database.models.mcp_authorization import (
    MCPResourceGrant,
    MCPServicePrincipal,
)
from ..database.models.message import utc_now
from ..database.orm_crud import create, exists, get_one, update
from ..services.mcp_server.contracts import (
    BotAddress,
    ConversationAddress,
    ResourceGrant,
    ServicePrincipal,
)

if TYPE_CHECKING:
    from ..services.mcp_server.administration import (
        CreateResourceGrantRequest,
        CreateServicePrincipalRequest,
        OAuthIdentityKind,
    )

_GRANT_UPDATE_LOST = "resource grant disappeared after update"
_CAS_ATTEMPTS = 3


def _principal_contract(model: MCPServicePrincipal) -> ServicePrincipal:
    return ServicePrincipal(
        principal_id=model.principal_id,
        display_name=model.display_name,
        enabled=model.enabled,
    )


def _grant_contract(model: MCPResourceGrant) -> ResourceGrant:
    return ResourceGrant(
        grant_id=model.grant_id,
        principal_id=model.principal_id,
        bot=BotAddress(
            model.platform_id,
            model.adapter_id,
            model.protocol_id,
            model.bot_id,
        ),
        conversation=ConversationAddress(
            model.conversation_type,
            model.conversation_id,
        ),
        revision=model.revision,
    )


async def create_service_principal(
    request: CreateServicePrincipalRequest,
) -> ServicePrincipal:
    existing = await get_one(
        MCPServicePrincipal,
        {
            "issuer": request.issuer,
            "identity_kind": request.identity_kind.value,
            "identity_value": request.identity_value,
        },
    )
    if existing is not None:
        return _principal_contract(existing)
    model = await create(
        MCPServicePrincipal,
        principal_id=request.principal_id,
        issuer=request.issuer,
        identity_kind=request.identity_kind.value,
        identity_value=request.identity_value,
        display_name=request.display_name,
        enabled=True,
    )
    return _principal_contract(model)


async def resolve_service_principal(
    *, issuer: str, identity_kind: OAuthIdentityKind, identity_value: str
) -> ServicePrincipal | None:
    model = await get_one(
        MCPServicePrincipal,
        {
            "issuer": issuer,
            "identity_kind": identity_kind.value,
            "identity_value": identity_value,
        },
    )
    return None if model is None else _principal_contract(model)


async def set_service_principal_enabled(principal_id: str, *, enabled: bool) -> bool:
    affected, rowcount_known = await update(
        MCPServicePrincipal,
        {"principal_id": principal_id},
        {"enabled": enabled},
    )
    return not rowcount_known or affected > 0


def _resource_filters(request: CreateResourceGrantRequest) -> dict[str, object]:
    return {
        "principal_id": request.principal_id,
        "platform_id": request.bot.platform_id,
        "adapter_id": request.bot.adapter_id,
        "protocol_id": request.bot.protocol_id,
        "bot_id": request.bot.bot_id,
        "conversation_type": request.conversation.conversation_type,
        "conversation_id": request.conversation.conversation_id,
    }


async def create_resource_grant(request: CreateResourceGrantRequest) -> ResourceGrant:
    filters = _resource_filters(request)
    for _attempt in range(_CAS_ATTEMPTS):
        existing = await get_one(MCPResourceGrant, filters)
        if existing is None:
            model = await create(
                MCPResourceGrant,
                grant_id=request.grant_id,
                revision=1,
                **filters,
            )
            return _grant_contract(model)
        if existing.revoked_at is None:
            return _grant_contract(existing)
        next_revision = existing.revision + 1
        affected, rowcount_known = await update(
            MCPResourceGrant,
            {
                "grant_id": existing.grant_id,
                "revision": existing.revision,
                "revoked_at": existing.revoked_at,
            },
            {"revision": next_revision, "revoked_at": None},
        )
        if affected > 0 or not rowcount_known:
            model = await get_one(MCPResourceGrant, {"grant_id": existing.grant_id})
            if (
                model is not None
                and model.revision == next_revision
                and model.revoked_at is None
            ):
                return _grant_contract(model)
    raise RuntimeError(_GRANT_UPDATE_LOST)


async def find_exact_resource_grant(
    *,
    principal_id: str,
    bot: BotAddress,
    conversation: ConversationAddress,
) -> ResourceGrant | None:
    model = await get_one(
        MCPResourceGrant,
        {
            "principal_id": principal_id,
            "platform_id": bot.platform_id,
            "adapter_id": bot.adapter_id,
            "protocol_id": bot.protocol_id,
            "bot_id": bot.bot_id,
            "conversation_type": conversation.conversation_type,
            "conversation_id": conversation.conversation_id,
            "revoked_at": None,
        },
    )
    return None if model is None else _grant_contract(model)


async def has_any_active_grant(*, principal_id: str) -> bool:
    """Return whether a principal owns at least one non-revoked exact grant."""
    return await exists(
        MCPResourceGrant,
        {"principal_id": principal_id, "revoked_at": None},
    )


async def revoke_resource_grant(grant_id: str) -> bool:
    for _attempt in range(_CAS_ATTEMPTS):
        existing = await get_one(MCPResourceGrant, {"grant_id": grant_id})
        if existing is None or existing.revoked_at is not None:
            return False
        next_revision = existing.revision + 1
        revoked_at = utc_now()
        affected, rowcount_known = await update(
            MCPResourceGrant,
            {
                "grant_id": grant_id,
                "revision": existing.revision,
                "revoked_at": None,
            },
            {"revision": next_revision, "revoked_at": revoked_at},
        )
        if affected > 0:
            return True
        if not rowcount_known:
            model = await get_one(MCPResourceGrant, {"grant_id": grant_id})
            if (
                model is not None
                and model.revision == next_revision
                and model.revoked_at == revoked_at
            ):
                return True
    return False
