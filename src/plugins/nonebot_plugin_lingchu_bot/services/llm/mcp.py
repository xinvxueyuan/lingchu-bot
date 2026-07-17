"""Managed MCP tool discovery with lazy optional-SDK loading."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
import json
import os
from typing import Literal, Protocol, cast, overload, override
from urllib.parse import urlparse, urlunparse

from httpx import AsyncBaseTransport, AsyncClient, AsyncHTTPTransport, Request, Response

from ...core.http_security import resolve_host_addresses, validate_public_http_url
from .config import MCPRuntimeConfig, MCPServerConfig
from .security import freeze_value, sanitize_message

CONTROL_CHAR_LIMIT = 32
MAX_TOOL_NAME_LENGTH = 128
MAX_TOOL_DESCRIPTION_LENGTH = 4096


class MCPError(RuntimeError):
    """Base error for managed MCP operations."""


class MCPRuntimeClosedError(MCPError):
    """The MCP runtime no longer accepts work."""


class MCPConfigurationError(MCPError):
    """Runtime-only MCP configuration is missing or invalid."""


class MCPConnectionError(MCPError):
    """An MCP transport or session could not be initialized."""


class MCPToolMetadataError(MCPError):
    """An MCP server returned invalid tool metadata."""


class MCPProtocolError(MCPError):
    """An MCP server request failed or returned an invalid response."""


class MCPToolTimeoutError(MCPProtocolError):
    """A tool call exceeded its configured per-call timeout."""


class MCPToolSchemaError(MCPError, TypeError):
    """An MCP server returned a non-mapping tool schema."""


class MCPSession(Protocol):
    """Small SDK-independent session surface owned by Lingchu Bot."""

    async def initialize(self) -> object: ...

    async def list_tools(self) -> object: ...

    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> object: ...


type MCPConnector = Callable[[MCPServerConfig], AbstractAsyncContextManager[object]]


@dataclass(frozen=True, slots=True)
class MCPToolDescriptor:
    """Validated tool metadata exposed to an MCP Agent."""

    server_name: str
    name: str
    description: str | None
    input_schema: Mapping[str, object]

    @property
    def qualified_name(self) -> str:
        """Return the stable model-facing tool name."""
        return f"{self.server_name}.{self.name}"


@dataclass(frozen=True, slots=True)
class MCPToolResult:
    """Bounded text projection of an untrusted MCP result."""

    content: str
    truncated: bool = False


class MCPRuntime:
    """Own lazy MCP sessions and expose namespaced tool discovery."""

    def __init__(
        self,
        config: MCPRuntimeConfig,
        *,
        connector: MCPConnector | None = None,
    ) -> None:
        self.config = config
        self._connector = connector or _connect_sdk_session
        self._stack = AsyncExitStack()
        self._sessions: dict[str, MCPSession] = {}
        self._lock = asyncio.Lock()
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None

    async def list_tools(self) -> tuple[MCPToolDescriptor, ...]:
        """Discover validated tools from every configured server."""
        if not self.config.enabled:
            return ()
        async with self._lock:
            if self._closed:
                raise MCPRuntimeClosedError
            tools: list[MCPToolDescriptor] = []
            for server in self.config.servers:
                session = await self._session(server)
                tools.extend(await _list_server_tools(server.name, session))
            return tuple(tools)

    async def call_tool(
        self, qualified_name: str, arguments: Mapping[str, object]
    ) -> MCPToolResult:
        """Invoke one namespaced tool and return bounded untrusted content."""
        server_name, separator, tool_name = qualified_name.partition(".")
        if not separator or not tool_name:
            raise MCPProtocolError
        try:
            server = next(
                item for item in self.config.servers if item.name == server_name
            )
        except StopIteration:
            raise MCPProtocolError from None
        frozen = _freeze_tool_arguments(arguments)
        try:
            async with asyncio.timeout(self.config.tool_timeout):
                async with self._lock:
                    session = await self._session(server)
                result = await session.call_tool(tool_name, frozen)
            content = _result_text(result)
        except asyncio.CancelledError:
            raise
        except MCPError:
            raise
        except TimeoutError:
            raise MCPToolTimeoutError from None
        except (TypeError, ValueError):
            raise MCPProtocolError from None
        except Exception:
            raise MCPProtocolError from None
        encoded = content.encode("utf-8")
        limit = self.config.result_limit_bytes
        if len(encoded) <= limit:
            return MCPToolResult(content=content)
        bounded = encoded[:limit].decode("utf-8", errors="ignore")
        return MCPToolResult(content=bounded, truncated=True)

    async def close(self) -> None:
        """Close every owned MCP session and transport once."""
        async with self._lock:
            if self._close_task is None:
                self._closed = True
                self._close_task = asyncio.create_task(self._stack.aclose())
            await asyncio.shield(self._close_task)
            self._sessions.clear()

    async def _session(self, server: MCPServerConfig) -> MCPSession:
        if self._closed:
            raise MCPRuntimeClosedError
        if session := self._sessions.get(server.name):
            return session
        pending = AsyncExitStack()
        try:
            connected = await pending.enter_async_context(self._connector(server))
            session = cast("MCPSession", connected)
            await session.initialize()
        except asyncio.CancelledError:
            await pending.aclose()
            raise
        except Exception:
            await pending.aclose()
            raise MCPConnectionError from None
        owned = pending.pop_all()
        self._stack.push_async_callback(owned.aclose)
        self._sessions[server.name] = session
        return session


@overload
def _plain_text(value: object, *, required: Literal[True]) -> str: ...


@overload
def _plain_text(value: object, *, required: Literal[False] = False) -> str | None: ...


def _plain_text(value: object, *, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_TOOL_NAME_LENGTH
        or any(ord(char) < CONTROL_CHAR_LIMIT for char in value)
    ):
        raise MCPToolMetadataError
    return value


def _description(value: object) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_TOOL_DESCRIPTION_LENGTH
        or any(ord(char) < CONTROL_CHAR_LIMIT for char in value)
    ):
        raise MCPToolMetadataError
    return value


def _headers_from_env(name: str | None) -> dict[str, str] | None:
    if not name:
        return None
    raw = os.environ.get(name)
    if not raw:
        raise MCPConfigurationError
    value: object = json.loads(raw)
    if not isinstance(value, dict):
        raise MCPConfigurationError
    mapping = cast("dict[object, object]", value)
    if not all(
        isinstance(key, str) and isinstance(item, str) for key, item in mapping.items()
    ):
        raise MCPConfigurationError
    return cast("dict[str, str]", mapping)


def _freeze_tool_arguments(
    arguments: Mapping[str, object],
) -> Mapping[str, object]:
    try:
        frozen = freeze_value(dict(arguments))
    except TypeError:
        raise MCPProtocolError from None
    if not isinstance(frozen, Mapping):
        raise MCPProtocolError
    return cast("Mapping[str, object]", frozen)


async def _list_server_tools(
    server_name: str, session: MCPSession
) -> tuple[MCPToolDescriptor, ...]:
    try:
        result = await session.list_tools()
    except asyncio.CancelledError:
        raise
    except Exception:
        raise MCPProtocolError from None
    try:
        descriptors: list[MCPToolDescriptor] = []
        seen: set[str] = set()
        for tool in getattr(result, "tools", ()):
            descriptor = _tool_descriptor(server_name, tool)
            _record_tool_name(seen, descriptor.name)
            descriptors.append(descriptor)
    except asyncio.CancelledError:
        raise
    except MCPError:
        raise
    except Exception:
        raise MCPProtocolError from None
    return tuple(descriptors)


def _record_tool_name(seen: set[str], name: str) -> None:
    if name in seen:
        raise MCPToolMetadataError
    seen.add(name)


def _tool_descriptor(server_name: str, tool: object) -> MCPToolDescriptor:
    name = _plain_text(getattr(tool, "name", None), required=True)
    description = _description(getattr(tool, "description", None))
    schema = getattr(tool, "inputSchema", None)
    if not isinstance(schema, Mapping):
        raise MCPToolSchemaError
    schema_mapping = cast("Mapping[str, object]", schema)
    try:
        frozen_schema = freeze_value(dict(schema_mapping))
    except TypeError:
        raise MCPToolSchemaError from None
    if not isinstance(frozen_schema, Mapping):
        raise MCPToolSchemaError
    return MCPToolDescriptor(
        server_name=server_name,
        name=name,
        description=sanitize_message(description) if description is not None else None,
        input_schema=cast("Mapping[str, object]", frozen_schema),
    )


def _result_text(result: object) -> str:
    model_dump = getattr(result, "model_dump", None)
    if callable(model_dump):
        result = model_dump(mode="json")
    return json.dumps(result, ensure_ascii=True, separators=(",", ":"))


class PinnedAddressTransport(AsyncBaseTransport):
    """Connect one HTTP origin to a previously validated address."""

    def __init__(
        self,
        *,
        origin_url: str,
        address: str,
        transport: AsyncBaseTransport | None = None,
    ) -> None:
        parsed = urlparse(origin_url)
        self._origin_host = parsed.hostname or ""
        default_port = 443 if parsed.scheme == "https" else 80
        self._origin_port = None if parsed.port == default_port else parsed.port
        self._address = address
        self._transport = transport or AsyncHTTPTransport()

    @override
    async def handle_async_request(self, request: Request) -> Response:
        if (
            request.url.host != self._origin_host
            or request.url.port != self._origin_port
        ):
            raise MCPConnectionError
        headers = request.headers.copy()
        default_port = 443 if request.url.scheme == "https" else 80
        host = self._origin_host
        if self._origin_port is not None and self._origin_port != default_port:
            host = f"{host}:{self._origin_port}"
        headers["host"] = host
        extensions = dict(request.extensions)
        extensions["sni_hostname"] = self._origin_host
        pinned = Request(
            request.method,
            request.url.copy_with(host=self._address),
            headers=headers,
            content=request.stream,
            extensions=extensions,
        )
        return await self._transport.handle_async_request(pinned)

    @override
    async def aclose(self) -> None:
        await self._transport.aclose()


async def _public_http_transport(url: str) -> PinnedAddressTransport:
    await validate_public_http_url(url)
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = await resolve_host_addresses(hostname, port)
    for address in addresses:
        literal_host = f"[{address}]" if ":" in address else address
        literal_url = urlunparse(parsed._replace(netloc=f"{literal_host}:{port}"))
        await validate_public_http_url(literal_url)
    if not addresses:
        raise MCPConnectionError
    return PinnedAddressTransport(origin_url=url, address=sorted(addresses)[0])


@asynccontextmanager
async def _connect_sdk_session(server: MCPServerConfig) -> AsyncGenerator[object]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamable_http_client

    if server.transport == "stdio":
        params = StdioServerParameters(
            command=server.command or "", args=list(server.args)
        )
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            yield session
        return

    transport = None
    if not server.allow_private_network:
        transport = await _public_http_transport(server.url or "")
    async with (
        AsyncClient(
            headers=_headers_from_env(server.headers_env),
            follow_redirects=False,
            transport=transport,
        ) as http_client,
        streamable_http_client(server.url or "", http_client=http_client) as (
            read,
            write,
            _,
        ),
        ClientSession(read, write) as session,
    ):
        yield session


__all__ = [
    "MCPConfigurationError",
    "MCPConnectionError",
    "MCPError",
    "MCPProtocolError",
    "MCPRuntime",
    "MCPRuntimeClosedError",
    "MCPToolDescriptor",
    "MCPToolMetadataError",
    "MCPToolResult",
    "MCPToolSchemaError",
    "MCPToolTimeoutError",
]
