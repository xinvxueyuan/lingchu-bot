from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from contextlib import asynccontextmanager
import inspect
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast, override
from unittest.mock import AsyncMock

from httpx import AsyncBaseTransport, Request, Response
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.http_security import (
    UnsafeDownloadURLError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm import mcp as mcp_module
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    MCPRuntimeConfig,
    MCPServerConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.mcp import (
    MCPConnectionError,
    MCPProtocolError,
    MCPRuntime,
    MCPToolMetadataError,
    MCPToolResult,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def test_list_tools_connects_lazily_and_namespaces_tools() -> None:
    calls: list[str] = []

    class FakeSession:
        async def initialize(self) -> None:
            calls.append("initialize")

        async def list_tools(self) -> object:
            calls.append("list_tools")
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="search",
                        description="Search documentation",
                        inputSchema={"type": "object"},
                    )
                ]
            )

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        calls.append("connect")
        yield FakeSession()

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(
                MCPServerConfig(
                    name="docs",
                    transport="streamable_http",
                    url="https://mcp.example/rpc",
                ),
            ),
        ),
        connector=connect,
    )

    assert calls == []

    tools = await runtime.list_tools()

    assert calls == ["connect", "initialize", "list_tools"]
    assert tools[0].qualified_name == "docs.search"
    assert tools[0].server_name == "docs"
    assert tools[0].name == "search"
    assert tools[0].input_schema == {"type": "object"}

    await runtime.close()


async def test_call_tool_routes_qualified_name_and_bounds_untrusted_result() -> None:
    received: list[tuple[str, Mapping[str, object]]] = []

    class FakeSession:
        async def initialize(self) -> None: ...

        async def list_tools(self) -> object:
            return SimpleNamespace(tools=[])

        async def call_tool(self, name: str, arguments: Mapping[str, object]) -> object:
            received.append((name, arguments))
            return {"content": "abcdef"}

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        yield FakeSession()

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            result_limit_bytes=5,
            servers=(MCPServerConfig(name="docs", transport="stdio", command="x"),),
        ),
        connector=connect,
    )

    result = await runtime.call_tool("docs.search", {"query": "python"})

    assert received == [("search", {"query": "python"})]
    assert result == MCPToolResult(content='{"con', truncated=True)


async def test_disabled_runtime_does_not_connect_or_load_sdk() -> None:
    called = False

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        nonlocal called
        called = True
        yield FakeSession()

    class FakeSession:
        async def initialize(self) -> None: ...

        async def list_tools(self) -> object: ...

    sys.modules.pop("mcp", None)
    runtime = MCPRuntime(MCPRuntimeConfig(), connector=connect)

    assert await runtime.list_tools() == ()
    assert called is False
    assert "mcp" not in sys.modules


async def test_initialize_failure_closes_transport_and_normalizes_error() -> None:
    closed = False

    class FailingSession:
        async def initialize(self) -> None:
            raise OSError("secret transport detail")

        async def list_tools(self) -> object: ...

    @asynccontextmanager
    async def connect(
        _server: MCPServerConfig,
    ) -> AsyncGenerator[FailingSession]:
        nonlocal closed
        try:
            yield FailingSession()
        finally:
            closed = True

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(
                MCPServerConfig(name="local", transport="stdio", command="server"),
            ),
        ),
        connector=connect,
    )

    with pytest.raises(MCPConnectionError):
        await runtime.list_tools()

    assert closed is True


async def test_http_server_revalidates_public_dns_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validate = AsyncMock(side_effect=UnsafeDownloadURLError)
    monkeypatch.setattr(mcp_module, "validate_public_http_url", validate)
    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(
                MCPServerConfig(
                    name="remote",
                    transport="streamable_http",
                    url="https://mcp.example/rpc",
                ),
            ),
        )
    )

    with pytest.raises(MCPConnectionError):
        await runtime.list_tools()

    validate.assert_awaited_once_with("https://mcp.example/rpc")


async def test_public_http_transport_connects_to_validated_address() -> None:
    requests: list[Request] = []

    class RecordingTransport(AsyncBaseTransport):
        @override
        async def handle_async_request(self, request: Request) -> Response:
            requests.append(request)
            return Response(200, request=request)

    transport = mcp_module.PinnedAddressTransport(
        origin_url="https://mcp.example/rpc",
        address="203.0.113.10",
        transport=RecordingTransport(),
    )
    request = Request("POST", "https://mcp.example/rpc")

    await transport.handle_async_request(request)

    sent = requests[0]
    assert sent.url.host == "203.0.113.10"
    assert sent.headers["host"] == "mcp.example"
    assert sent.extensions["sni_hostname"] == "mcp.example"


@pytest.mark.parametrize(
    ("origin_url", "request_url"),
    [
        ("http://mcp.example:80/rpc", "http://mcp.example/rpc"),
        ("https://mcp.example:443/rpc", "https://mcp.example/rpc"),
    ],
)
async def test_public_http_transport_accepts_normalized_default_ports(
    origin_url: str, request_url: str
) -> None:
    requests: list[Request] = []

    class RecordingTransport(AsyncBaseTransport):
        @override
        async def handle_async_request(self, request: Request) -> Response:
            requests.append(request)
            return Response(200, request=request)

    transport = mcp_module.PinnedAddressTransport(
        origin_url=origin_url,
        address="203.0.113.10",
        transport=RecordingTransport(),
    )

    await transport.handle_async_request(Request("POST", request_url))

    assert requests[0].headers["host"] == "mcp.example"


async def test_close_waits_for_first_connection_and_closes_it() -> None:
    connecting = asyncio.Event()
    release = asyncio.Event()
    closed = False

    class FakeSession:
        async def initialize(self) -> None:
            connecting.set()
            await release.wait()

        async def list_tools(self) -> object:
            return SimpleNamespace(tools=[])

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        nonlocal closed
        try:
            yield FakeSession()
        finally:
            closed = True

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(MCPServerConfig(name="local", transport="stdio", command="x"),),
        ),
        connector=connect,
    )
    listing = asyncio.create_task(runtime.list_tools())
    await connecting.wait()
    closing = asyncio.create_task(runtime.close())
    await asyncio.sleep(0)

    assert closing.done() is False
    release.set()
    await listing
    await closing

    assert closed is True


async def test_cancelled_close_can_be_retried_until_cleanup_finishes() -> None:
    cleanup_started = asyncio.Event()
    release_cleanup = asyncio.Event()
    cleanup_finished = False

    class FakeSession:
        async def initialize(self) -> None: ...

        async def list_tools(self) -> object:
            return SimpleNamespace(tools=[])

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        nonlocal cleanup_finished
        try:
            yield FakeSession()
        finally:
            cleanup_started.set()
            await release_cleanup.wait()
            cleanup_finished = True

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(MCPServerConfig(name="local", transport="stdio", command="x"),),
        ),
        connector=connect,
    )
    await runtime.list_tools()
    closing = asyncio.create_task(runtime.close())
    await cleanup_started.wait()

    closing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closing
    release_cleanup.set()
    await runtime.close()

    assert cleanup_finished is True


@pytest.mark.parametrize("hostile_result", ["property", "iterator"])
async def test_hostile_tool_collection_is_normalized(hostile_result: str) -> None:
    class HostileResult:
        @property
        def tools(self) -> object:
            if hostile_result == "property":
                raise RuntimeError("secret property detail")
            return HostileIterator()

    class HostileIterator:
        def __iter__(self) -> Iterator[object]:
            raise RuntimeError("secret iterator detail")

    class FakeSession:
        async def initialize(self) -> None: ...

        async def list_tools(self) -> object:
            return HostileResult()

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        yield FakeSession()

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(MCPServerConfig(name="local", transport="stdio", command="x"),),
        ),
        connector=connect,
    )

    with pytest.raises(MCPProtocolError):
        await runtime.list_tools()


async def test_description_has_independent_bounded_length() -> None:
    description = "d" * 1024

    class FakeSession:
        async def initialize(self) -> None: ...

        async def list_tools(self) -> object:
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="search", description=description, inputSchema={}
                    )
                ]
            )

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        yield FakeSession()

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(MCPServerConfig(name="local", transport="stdio", command="x"),),
        ),
        connector=connect,
    )

    assert (await runtime.list_tools())[0].description == description

    description = "d" * (mcp_module.MAX_TOOL_DESCRIPTION_LENGTH + 1)
    with pytest.raises(MCPToolMetadataError):
        await runtime.list_tools()


async def test_tool_schema_is_deeply_frozen() -> None:
    query_schema = {"type": "string"}
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"query": query_schema},
    }

    class FakeSession:
        async def initialize(self) -> None: ...

        async def list_tools(self) -> object:
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="search",
                        description="Search",
                        inputSchema=schema,
                    )
                ]
            )

    @asynccontextmanager
    async def connect(_server: MCPServerConfig) -> AsyncGenerator[FakeSession]:
        yield FakeSession()

    runtime = MCPRuntime(
        MCPRuntimeConfig(
            enabled=True,
            review_profile="reviewer",
            servers=(
                MCPServerConfig(name="docs", transport="stdio", command="server"),
            ),
        ),
        connector=connect,
    )

    tool = (await runtime.list_tools())[0]
    query_schema["type"] = "number"

    properties = cast("Mapping[str, object]", tool.input_schema["properties"])
    assert isinstance(properties, Mapping)
    query = cast("Mapping[str, object]", properties["query"])
    assert isinstance(query, Mapping)
    assert query["type"] == "string"


def test_installed_mcp_sdk_exposes_supported_client_contract() -> None:
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamable_http_client

    assert callable(stdio_client)
    assert "http_client" in inspect.signature(streamable_http_client).parameters
