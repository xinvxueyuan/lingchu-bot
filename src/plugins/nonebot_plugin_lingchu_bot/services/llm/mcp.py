"""Managed MCP tool discovery backed by the Pydantic AI MCPToolset.

The runtime owns one :class:`pydantic_ai.mcp.MCPToolset` per configured
server (constructed lazily on first access). Public DTOs
(:class:`MCPToolDescriptor`, :class:`MCPToolResult`) are preserved so
existing call sites continue to type-check.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from typing import TYPE_CHECKING, Any, Literal, cast, overload

from fastmcp.client import Client as FastMCPClient
from fastmcp.client.transports.http import StreamableHttpTransport
from fastmcp.client.transports.stdio import StdioTransport
from pydantic_ai.mcp import MCPToolset

from .security import freeze_value, sanitize_message

if TYPE_CHECKING:
    from .config import MCPConfig, MCPServerDef

CONTROL_CHAR_LIMIT = 32
MAX_TOOL_NAME_LENGTH = 128
MAX_TOOL_DESCRIPTION_LENGTH = 4096
DEFAULT_TOOL_TIMEOUT = 15.0
DEFAULT_RESULT_LIMIT_BYTES = 65536


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
    """Own lazy Pydantic AI MCPToolsets and expose namespaced tool discovery."""

    def __init__(self, config: MCPConfig) -> None:
        self.config = config
        self._toolsets: dict[str, MCPToolset[Any]] = {}
        self._lock = asyncio.Lock()
        self._closed = False

    async def toolsets(self) -> tuple[MCPToolset[Any], ...]:
        """Lazily construct and return every configured MCPToolset.

        Returns an empty tuple when MCP is disabled. Construction is
        serialized through an :class:`asyncio.Lock` so concurrent first
        callers do not race to build the same toolset.
        """
        if not self.config.enabled:
            return ()
        async with self._lock:
            if self._closed:
                raise MCPRuntimeClosedError
            for name, server in self.config.servers.items():
                if name not in self._toolsets:
                    self._toolsets[name] = _build_toolset(name, server)
            return tuple(self._toolsets.values())

    async def list_tools(self) -> tuple[MCPToolDescriptor, ...]:
        """Discover validated tools from every configured server.

        Delegates to each MCPToolset's underlying FastMCPClient and maps
        the MCP ``Tool`` objects into stable ``MCPToolDescriptor`` DTOs.
        """
        toolsets = await self.toolsets()
        if not toolsets:
            return ()
        descriptors: list[MCPToolDescriptor] = []
        seen: set[str] = set()
        for toolset in toolsets:
            server_name = toolset.id
            if not server_name:
                continue
            try:
                tools = await toolset.list_tools()
            except asyncio.CancelledError:
                raise
            except Exception:
                raise MCPProtocolError from None
            for tool in tools:
                descriptor = _tool_descriptor(server_name, tool)
                _record_tool_name(seen, descriptor.name)
                descriptors.append(descriptor)
        return tuple(descriptors)

    async def call_tool(
        self, qualified_name: str, arguments: Mapping[str, object]
    ) -> MCPToolResult:
        """Invoke one namespaced tool and return bounded untrusted content."""
        server_name, separator, tool_name = qualified_name.partition(".")
        if not separator or not tool_name:
            raise MCPProtocolError
        toolset = await self._toolset_for(server_name)
        frozen = _freeze_tool_arguments(arguments)
        try:
            async with asyncio.timeout(DEFAULT_TOOL_TIMEOUT):
                result = await toolset.direct_call_tool(tool_name, dict(frozen))
        except asyncio.CancelledError:
            raise
        except MCPError:
            raise
        except TimeoutError:
            raise MCPToolTimeoutError from None
        except Exception:
            raise MCPProtocolError from None
        content = _result_text(result)
        encoded = content.encode("utf-8")
        if len(encoded) <= DEFAULT_RESULT_LIMIT_BYTES:
            return MCPToolResult(content=content)
        bounded = encoded[:DEFAULT_RESULT_LIMIT_BYTES].decode("utf-8", errors="ignore")
        return MCPToolResult(content=bounded, truncated=True)

    async def close(self) -> None:
        """Close every owned MCPToolset once."""
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            for toolset in self._toolsets.values():
                try:
                    await toolset.client.close()
                except Exception:
                    continue
            self._toolsets.clear()

    async def _toolset_for(self, server_name: str) -> MCPToolset[Any]:
        if not self.config.enabled:
            raise MCPConfigurationError
        async with self._lock:
            if self._closed:
                raise MCPRuntimeClosedError
            if server_name not in self.config.servers:
                raise MCPProtocolError
            if server_name not in self._toolsets:
                self._toolsets[server_name] = _build_toolset(
                    server_name, self.config.servers[server_name]
                )
            return self._toolsets[server_name]


def _build_toolset(name: str, server: MCPServerDef) -> MCPToolset[Any]:
    """Construct a Pydantic AI MCPToolset from a server definition."""
    if server.transport == "stdio":
        if not server.command:
            raise MCPConfigurationError
        transport: Any = StdioTransport(command=server.command, args=list(server.args))
    elif server.transport == "streamable_http":
        if not server.url:
            raise MCPConfigurationError
        transport = StreamableHttpTransport(
            url=server.url, headers=_headers_from_env(server.headers_env)
        )
    else:
        # MCPServerDef is pydantic-validated so this is unreachable in
        # practice; the defensive check satisfies exhaustiveness auditing.
        raise MCPConfigurationError
    client = FastMCPClient(transport, timeout=DEFAULT_TOOL_TIMEOUT)
    return MCPToolset(client, id=name)


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
    schema_mapping = schema
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
