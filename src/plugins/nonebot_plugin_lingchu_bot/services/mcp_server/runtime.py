"""Production composition and host lifecycle for the inbound MCP server."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from time import monotonic
from typing import TYPE_CHECKING, Any, cast, override

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from nonebot import get_bots
from pydantic import AnyHttpUrl

from ...hooks.adapters import DEFAULT_PROTOCOL_ID, resolve_platform_context
from .administration import OAuthIdentityKind
from .auth import (
    AuthenticationError,
    AuthorizationError,
    AuthorizationPolicy,
    CatalogEntry,
    OAuthIssuerPolicy,
    ProjectTokenVerifier,
    TokenClaims,
    filter_catalog,
)
from .authorized_message_query import AuthorizedMessageQuery
from .bot_directory import BotDirectory
from .config import (
    MCPServerConfig,
    ensure_mcp_server_config_file_async,
    load_mcp_server_config,
)
from .contracts import (
    BotAddress,
    CapabilityScope,
    ContractError,
    ConversationAddress,
    ErrorCode,
    ImageSegment,
    ListRecentMessagesRequest,
    MessageCursor,
    SendMessageRequest,
    TextSegment,
)
from .cursor import CursorCodec
from .jwks import PyJWTJWKSDecoder
from .lifecycle import InboundMCPConfig, InboundMCPServer
from .message_query import RepositoryMessagePageSource
from .message_send import SendMessageAction
from .onebot11_messages import OneBotV11MessageProvider
from .persistence import MCPServerAudit, ScopedAuthorizationRepository
from .providers import ProviderRegistry
from .send_orchestrator import (
    IdempotencyLedger,
    SendLimits,
    SendMessageOrchestrator,
)

if TYPE_CHECKING:
    from mcp.types import Tool
    from nonebot.adapters import Bot

    from .auth import AuthenticatedPrincipal

_CATALOG_VERSION = "1"
_RATE_WINDOW_SECONDS = 60.0


class InboundMCPRuntimeError(RuntimeError):
    """Reject invalid production runtime composition."""

    def __init__(self) -> None:
        super().__init__("cannot build a disabled MCP server")


class _ReadLimiter:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._events: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, principal_id: str) -> None:
        async with self._lock:
            now = monotonic()
            events = [
                value
                for value in self._events.get(principal_id, ())
                if now - value < _RATE_WINDOW_SECONDS
            ]
            if len(events) >= self._limit:
                raise ContractError(
                    ErrorCode.RATE_LIMITED,
                    "message read rate limit exceeded",
                )
            events.append(now)
            self._events[principal_id] = events


class AuthorizedFastMCP(FastMCP[Any]):
    """FastMCP whose tool discovery is filtered by current project authority."""

    def configure_authorization(self, policy: AuthorizationPolicy) -> None:
        self._catalog_policy = policy

    @override
    async def list_tools(self) -> list[Tool]:
        authenticated = await self._catalog_policy.authenticate(_claims_from_context())
        catalog = (
            CatalogEntry(
                "bots.list",
                CapabilityScope.BOTS_LIST,
                resource_bound=False,
            ),
            CatalogEntry(
                "messages.list_recent",
                CapabilityScope.MESSAGES_READ,
                resource_bound=True,
            ),
            CatalogEntry(
                "messages.send",
                CapabilityScope.MESSAGES_SEND,
                resource_bound=True,
            ),
        )
        allowed = {
            entry.name
            for entry in await filter_catalog(
                self._catalog_policy,
                authenticated,
                catalog,
            )
        }
        return [tool for tool in await super().list_tools() if tool.name in allowed]


def _bot_address(bot: object) -> BotAddress:
    context = resolve_platform_context(cast("Bot", bot))
    if context is None:
        raise ContractError(ErrorCode.UNSUPPORTED_PLATFORM, "unsupported bot adapter")
    return BotAddress(
        context.platform_id,
        context.adapter_id,
        context.protocol_id or DEFAULT_PROTOCOL_ID,
        context.bot_id,
    )


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    raise TypeError


def _json_contract(value: object) -> dict[str, Any]:
    encoded = json.dumps(asdict(cast("Any", value)), default=_json_default)
    return cast("dict[str, Any]", json.loads(encoded))


def _claims_from_context() -> TokenClaims:
    access_token = get_access_token()
    if access_token is None or access_token.expires_at is None:
        raise AuthenticationError
    claims = access_token.claims or {}
    try:
        issuer = str(claims["iss"])
        identity_kind = OAuthIdentityKind(str(claims["identity_kind"]))
        identity_value = str(claims["identity_value"])
    except (KeyError, ValueError):
        raise AuthenticationError from None
    return TokenClaims(
        issuer=issuer,
        identity_kind=identity_kind,
        identity_value=identity_value,
        client_id=access_token.client_id,
        scopes=frozenset(access_token.scopes),
        expires_at=access_token.expires_at,
    )


def _segments(
    values: list[dict[str, str]],
) -> tuple[TextSegment | ImageSegment, ...]:
    segments: list[TextSegment | ImageSegment] = []
    for value in values:
        segment_type = value.get("type")
        if segment_type == "text" and set(value) == {"type", "text"}:
            segments.append(TextSegment(value["text"]))
        elif segment_type == "image" and set(value) == {"type", "url"}:
            segments.append(ImageSegment(value["url"]))
        else:
            raise ContractError(
                ErrorCode.INVALID_MESSAGE_SEGMENT,
                "segments must be exact text or image objects",
            )
    return tuple(segments)


@dataclass(slots=True)
class InboundMCPRuntime:
    """Own one fully composed inbound server and its connected-bot directory."""

    config: MCPServerConfig
    repository: ScopedAuthorizationRepository
    policy: AuthorizationPolicy
    bots: BotDirectory
    server: InboundMCPServer

    def connect_bot(self, bot: object) -> None:
        """Register a supported live bot using its trusted adapter context."""
        try:
            address = _bot_address(bot)
        except ContractError:
            return
        self.bots.connect(address, bot, display_name=address.bot_id)

    def disconnect_bot(self, bot: object) -> None:
        """Remove a bot only when the connection instance still matches."""
        try:
            address = _bot_address(bot)
        except ContractError:
            return
        self.bots.disconnect(address, bot)


def build_authenticated_server(
    config: MCPServerConfig,
    *,
    repository: ScopedAuthorizationRepository | None = None,
    bots: BotDirectory | None = None,
) -> tuple[
    FastMCP[Any],
    ScopedAuthorizationRepository,
    AuthorizationPolicy,
    BotDirectory,
]:
    """Compose the authenticated transport and project-owned operations."""
    config.validate_enabled()
    if not config.enabled:
        raise InboundMCPRuntimeError
    assert config.issuer is not None
    assert config.audience is not None
    assert config.jwks_url is not None
    assert config.cursor_secret_env is not None
    secret = os.environ[config.cursor_secret_env].encode()
    authorization_repository = repository or ScopedAuthorizationRepository()
    policy = AuthorizationPolicy(authorization_repository)
    directory = bots or BotDirectory(_bot_address)
    verifier = ProjectTokenVerifier(
        decoder=PyJWTJWKSDecoder(config.jwks_url),
        issuer_policy=OAuthIssuerPolicy(
            config.issuer,
            config.audience,
            config.identity_kind,
        ),
    )
    audit = MCPServerAudit()
    query = AuthorizedMessageQuery(
        policy=policy,
        source=RepositoryMessagePageSource(),
        cursor_codec=CursorCodec(secret=secret),
        audit=audit,
    )
    providers = ProviderRegistry((OneBotV11MessageProvider(),))
    sender = SendMessageOrchestrator(
        action=SendMessageAction(providers, directory),
        policy=policy,
        audit=audit,
        ledger=IdempotencyLedger(),
        limits=SendLimits(
            principal_rate_per_minute=config.send_rate_per_minute,
            conversation_rate_per_minute=(config.conversation_send_rate_per_minute),
            principal_concurrency=config.principal_concurrency,
            conversation_concurrency=(config.conversation_write_concurrency),
        ),
    )
    read_limiter = _ReadLimiter(config.read_rate_per_minute)
    server = AuthorizedFastMCP(
        "Lingchu Bot",
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(config.issuer),
            resource_server_url=AnyHttpUrl(config.audience),
            required_scopes=None,
        ),
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
    )
    server.configure_authorization(policy)

    async def authenticate() -> AuthenticatedPrincipal:
        return await policy.authenticate(_claims_from_context())

    @server.tool(name="bots.list")
    async def list_bots() -> dict[str, object]:
        authenticated = await authenticate()
        if (
            CapabilityScope.BOTS_LIST.value not in authenticated.scopes
            or not await policy.principal_is_current(authenticated)
        ):
            raise AuthorizationError
        grants = await authorization_repository.list_active_grants(
            principal_id=authenticated.principal.principal_id
        )
        allowed = frozenset(grant.bot for grant in grants)
        return {
            "bots": [
                _json_contract(summary) for summary in directory.list_connected(allowed)
            ]
        }

    @server.tool(name="messages.list_recent")
    async def list_recent_messages(
        platform_id: str,
        adapter_id: str,
        protocol_id: str,
        bot_id: str,
        conversation_type: str,
        conversation_id: str,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, object]:
        if limit > config.max_page_size:
            raise ContractError(
                ErrorCode.INVALID_LIMIT,
                "message page limit exceeded",
            )
        authenticated = await authenticate()
        await read_limiter.acquire(authenticated.principal.principal_id)
        result = await query.list_recent(
            authenticated,
            ListRecentMessagesRequest(
                BotAddress(platform_id, adapter_id, protocol_id, bot_id),
                ConversationAddress(conversation_type, conversation_id),
                limit,
                MessageCursor(cursor) if cursor is not None else None,
            ),
        )
        return {
            "messages": [_json_contract(message) for message in result.messages],
            "next_cursor": (
                result.next_cursor.value if result.next_cursor is not None else None
            ),
        }

    @server.tool(name="messages.send")
    async def send_message(
        platform_id: str,
        adapter_id: str,
        protocol_id: str,
        bot_id: str,
        conversation_type: str,
        conversation_id: str,
        segments: list[dict[str, str]],
        idempotency_key: str,
    ) -> dict[str, object]:
        authenticated = await authenticate()
        result = await sender.send(
            authenticated,
            SendMessageRequest(
                BotAddress(platform_id, adapter_id, protocol_id, bot_id),
                ConversationAddress(conversation_type, conversation_id),
                _segments(segments),
                idempotency_key,
            ),
        )
        return _json_contract(result)

    @server.resource("lingchu://server/info")
    async def server_info() -> dict[str, object]:
        authenticated = await authenticate()
        if not await policy.principal_is_current(authenticated):
            raise AuthorizationError
        return {
            "name": "Lingchu Bot",
            "catalog_version": _CATALOG_VERSION,
            "capabilities": sorted(authenticated.scopes),
        }

    @server.resource("lingchu://bots/{platform_id}/{adapter_id}/{protocol_id}/{bot_id}")
    async def bot_info(
        platform_id: str,
        adapter_id: str,
        protocol_id: str,
        bot_id: str,
    ) -> dict[str, object]:
        authenticated = await authenticate()
        address = BotAddress(
            platform_id,
            adapter_id,
            protocol_id,
            bot_id,
        )
        grants = await authorization_repository.list_active_grants(
            principal_id=authenticated.principal.principal_id
        )
        if not await policy.principal_is_current(authenticated) or not any(
            grant.bot == address for grant in grants
        ):
            raise AuthorizationError
        summaries = directory.list_connected(frozenset({address}))
        if not summaries:
            raise ContractError(
                ErrorCode.BOT_NOT_FOUND,
                "connected bot not found",
            )
        return _json_contract(summaries[0])

    return server, authorization_repository, policy, directory


class _ManagedRuntime:
    value: InboundMCPRuntime | None = None


async def initialize_inbound_mcp_runtime() -> InboundMCPRuntime | None:
    """Ensure config, mount once, and start the enabled inbound server."""
    if _ManagedRuntime.value is not None:
        return _ManagedRuntime.value
    await ensure_mcp_server_config_file_async()
    config = load_mcp_server_config()
    if not config.enabled:
        return None
    sdk_server, repository, policy, bots = build_authenticated_server(config)
    lifecycle = InboundMCPServer(
        InboundMCPConfig(enabled=True, route=config.route),
        build_server=lambda: sdk_server,
    )
    lifecycle.mount()
    await lifecycle.start()
    _ManagedRuntime.value = InboundMCPRuntime(
        config,
        repository,
        policy,
        bots,
        lifecycle,
    )
    for bot in get_bots().values():
        _ManagedRuntime.value.connect_bot(bot)
    return _ManagedRuntime.value


async def shutdown_inbound_mcp_runtime() -> None:
    """Stop and discard the currently managed inbound server."""
    runtime, _ManagedRuntime.value = _ManagedRuntime.value, None
    if runtime is not None:
        await runtime.server.stop()


def connect_inbound_mcp_bot(bot: object) -> None:
    """Synchronize one connection into the enabled runtime, if present."""
    if _ManagedRuntime.value is not None:
        _ManagedRuntime.value.connect_bot(bot)


def disconnect_inbound_mcp_bot(bot: object) -> None:
    """Synchronize one disconnection from the enabled runtime, if present."""
    if _ManagedRuntime.value is not None:
        _ManagedRuntime.value.disconnect_bot(bot)


__all__ = [
    "InboundMCPRuntime",
    "build_authenticated_server",
    "connect_inbound_mcp_bot",
    "disconnect_inbound_mcp_bot",
    "initialize_inbound_mcp_runtime",
    "shutdown_inbound_mcp_runtime",
]
