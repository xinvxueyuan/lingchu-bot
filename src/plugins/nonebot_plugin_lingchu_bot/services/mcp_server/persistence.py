"""Scoped persistence adapters for the inbound MCP control plane."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import json
from typing import TYPE_CHECKING

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ...repositories import mcp_authorization, message_store
from .authorized_message_query import SensitiveReadAuditError

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

    from .administration import OAuthIdentityKind
    from .auth import ResourceAuthorization
    from .contracts import (
        BotAddress,
        ConversationAddress,
        ResourceGrant,
        SendMessageResult,
        ServicePrincipal,
    )

type Session = AsyncSession | async_scoped_session[AsyncSession]
type SessionFactory = Callable[[], AbstractAsyncContextManager[Session]]
type AuditWriter = Callable[[Session, message_store.AuditEvent], Awaitable[object]]

_SUMMARY_LIMIT = 500


class MCPServerAuditUnavailableError(RuntimeError):
    """Signal that a mandatory inbound MCP audit could not be persisted."""


def _default_session_factory() -> AbstractAsyncContextManager[Session]:
    return get_session()


class ScopedAuthorizationRepository:
    """Open one ORM scope for each authorization-policy repository operation."""

    def __init__(
        self, session_factory: SessionFactory = _default_session_factory
    ) -> None:
        self._session_factory = session_factory

    async def resolve_principal(
        self, *, issuer: str, identity_kind: OAuthIdentityKind, identity_value: str
    ) -> ServicePrincipal | None:
        async with self._session_factory() as session:
            return await mcp_authorization.resolve_service_principal(
                session,
                issuer=issuer,
                identity_kind=identity_kind,
                identity_value=identity_value,
            )

    async def find_exact_grant(
        self, *, principal_id: str, bot: BotAddress, conversation: ConversationAddress
    ) -> ResourceGrant | None:
        async with self._session_factory() as session:
            return await mcp_authorization.find_exact_resource_grant(
                session, principal_id=principal_id, bot=bot, conversation=conversation
            )

    async def has_any_active_grant(self, *, principal_id: str) -> bool:
        async with self._session_factory() as session:
            return await mcp_authorization.has_any_active_grant(
                session, principal_id=principal_id
            )

    async def list_active_grants(
        self,
        *,
        principal_id: str,
    ) -> tuple[ResourceGrant, ...]:
        """Return the principal's current exact grants from one ORM scope."""
        async with self._session_factory() as session:
            return await mcp_authorization.list_active_resource_grants(
                session,
                principal_id=principal_id,
            )


def _summary(value: object) -> str:
    text = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, default=str
    )
    return text if len(text) <= _SUMMARY_LIMIT else text[:_SUMMARY_LIMIT]


class MCPServerAudit:
    """Persist fail-closed pre-operation and best-effort post-operation audits."""

    def __init__(
        self,
        session_factory: SessionFactory = _default_session_factory,
        writer: AuditWriter = message_store.record_api_call,
    ) -> None:
        self._session_factory = session_factory
        self._writer = writer

    @staticmethod
    def _event(
        authorization: ResourceAuthorization,
        *,
        api_name: str,
        data: object,
        result: str,
    ) -> message_store.AuditEvent:
        grant = authorization.grant
        return message_store.AuditEvent(
            platform_id=grant.bot.platform_id,
            adapter_id=grant.bot.adapter_id,
            protocol_id=grant.bot.protocol_id,
            bot_id=grant.bot.bot_id,
            api_name=api_name,
            data_summary=_summary(data),
            result_summary=result,
            exception_summary=None,
            audit_type="mcp_server",
        )

    async def _write(self, event: message_store.AuditEvent) -> None:
        async with self._session_factory() as session:
            await self._writer(session, event)

    async def record_pre_read(self, authorization: ResourceAuthorization) -> None:
        """Durably record authority before exposing stored message content."""
        try:
            await self._write(
                self._event(
                    authorization,
                    api_name="mcp.messages.list_recent",
                    data={
                        "grant_id": authorization.grant.grant_id,
                        "principal_id": authorization.grant.principal_id,
                        "conversation_type": (
                            authorization.grant.conversation.conversation_type
                        ),
                        "conversation_id": (
                            authorization.grant.conversation.conversation_id
                        ),
                    },
                    result="pre_read",
                )
            )
        except Exception:
            raise SensitiveReadAuditError from None

    async def record_pre_send(
        self, authorization: ResourceAuthorization, payload: dict[str, object]
    ) -> None:
        """Durably record authorization before an external message send."""
        try:
            await self._write(
                self._event(
                    authorization,
                    api_name="mcp.messages.send",
                    data=payload,
                    result="pre_send",
                )
            )
        except Exception as exc:
            raise MCPServerAuditUnavailableError from exc

    async def record_post_send(
        self,
        authorization: ResourceAuthorization,
        payload: dict[str, object],
        result: SendMessageResult,
    ) -> None:
        """Record the stable result after the platform call returns."""
        try:
            await self._write(
                self._event(
                    authorization,
                    api_name="mcp.messages.send",
                    data=payload,
                    result=_summary({
                        "error_code": result.error_code,
                        "operation_id": result.operation_id,
                        "platform_message_id": result.platform_message_id,
                        "status": result.status,
                    }),
                )
            )
        except Exception as exc:
            raise MCPServerAuditUnavailableError from exc


__all__ = [
    "MCPServerAudit",
    "MCPServerAuditUnavailableError",
    "ScopedAuthorizationRepository",
]
