"""Tests for the Pydantic AI MCPToolset-backed MCPRuntime."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from types import SimpleNamespace
from typing import Literal, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import mcp as mcp_module
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    MCPConfig,
    MCPServerDef,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.mcp import (
    MCPConfigurationError,
    MCPProtocolError,
    MCPRuntime,
    MCPRuntimeClosedError,
    MCPToolDescriptor,
    MCPToolMetadataError,
    MCPToolResult,
    MCPToolSchemaError,
    MCPToolTimeoutError,
)


def _server_def(
    *,
    transport: Literal["stdio", "streamable_http"] = "stdio",
    command: str | None = "echo",
    url: str | None = None,
    headers_env: str | None = None,
) -> MCPServerDef:
    return MCPServerDef(
        transport=transport,
        command=command,
        url=url,
        headers_env=headers_env,
    )


def _config(
    *,
    enabled: bool = True,
    servers: Mapping[str, MCPServerDef] | None = None,
) -> MCPConfig:
    return MCPConfig(
        enabled=enabled,
        servers=dict(servers or {}),
    )


def _fake_tool(
    *,
    name: str = "search",
    description: str | None = "Search documentation",
    schema: Mapping[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        description=description,
        inputSchema=dict(schema or {"type": "object"}),
    )


def _fake_toolset(
    *,
    server_name: str = "docs",
    tools: list[SimpleNamespace] | None = None,
    list_tools_side_effect: object | None = None,
) -> MagicMock:
    toolset = MagicMock(name=f"toolset-{server_name}")
    toolset.id = server_name
    if list_tools_side_effect is not None:
        toolset.list_tools = AsyncMock(side_effect=list_tools_side_effect)
    else:
        toolset.list_tools = AsyncMock(return_value=list(tools or []))
    toolset.direct_call_tool = AsyncMock(return_value=SimpleNamespace(content="ok"))
    toolset.client = MagicMock()
    toolset.client.close = AsyncMock()
    return toolset


def _patch_build_toolset(
    monkeypatch: pytest.MonkeyPatch,
    toolsets: dict[str, MagicMock] | None = None,
    builder: Callable[[str, MCPServerDef], MagicMock] | None = None,
) -> dict[str, MagicMock]:
    """Patch ``mcp_module._build_toolset`` to return mock toolsets.

    The captured dict is populated lazily as the runtime builds each server's
    toolset, so callers can assert against the constructed mocks afterwards.
    """
    captured: dict[str, MagicMock] = toolsets or {}

    def _build(name: str, server: MCPServerDef) -> MagicMock:
        if name not in captured:
            if builder is not None:
                captured[name] = builder(name, server)
            else:
                captured[name] = _fake_toolset(server_name=name)
        return captured[name]

    monkeypatch.setattr(mcp_module, "_build_toolset", _build)
    return captured


def _cast_mapping(value: object) -> Mapping[str, object]:
    assert isinstance(value, Mapping)
    return cast("Mapping[str, object]", value)


async def test_disabled_runtime_returns_empty_toolsets_and_descriptors() -> None:
    runtime = MCPRuntime(_config(enabled=False))

    assert await runtime.toolsets() == ()
    assert await runtime.list_tools() == ()


async def test_toolsets_constructs_one_per_server_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch_build_toolset(monkeypatch)

    runtime = MCPRuntime(
        _config(
            servers={
                "docs": _server_def(),
                "files": _server_def(command="ls"),
            },
        )
    )

    first = await runtime.toolsets()
    second = await runtime.toolsets()

    assert set(captured.keys()) == {"docs", "files"}
    assert first == second
    assert len(first) == 2
    assert first[0] is captured["docs"]
    assert first[1] is captured["files"]


async def test_list_tools_maps_toolset_tools_to_descriptors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(
        server_name="docs",
        tools=[_fake_tool(name="search", description="Search documentation")],
    )
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    tools = await runtime.list_tools()

    assert len(tools) == 1
    tool = tools[0]
    assert isinstance(tool, MCPToolDescriptor)
    assert tool.server_name == "docs"
    assert tool.name == "search"
    assert tool.description == "Search documentation"
    assert tool.input_schema == {"type": "object"}
    assert tool.qualified_name == "docs.search"
    toolset.list_tools.assert_awaited_once()


async def test_list_tools_freezes_schema_deeply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nested: dict[str, object] = {"type": "string"}
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"query": nested},
    }
    toolset = _fake_toolset(
        server_name="docs",
        tools=[_fake_tool(name="search", schema=schema)],
    )
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))
    tool = (await runtime.list_tools())[0]

    nested["type"] = "number"
    properties = _cast_mapping(tool.input_schema["properties"])
    query = _cast_mapping(properties["query"])
    assert query["type"] == "string"


async def test_list_tools_skips_toolset_without_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(server_name="docs")
    toolset.id = ""
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    assert await runtime.list_tools() == ()


async def test_list_tools_raises_protocol_error_when_toolset_list_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(
        server_name="docs",
        list_tools_side_effect=RuntimeError("transport gone"),
    )
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(MCPProtocolError):
        await runtime.list_tools()


async def test_list_tools_rejects_duplicate_tool_names_across_servers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolsets = {
        "docs": _fake_toolset(
            server_name="docs",
            tools=[_fake_tool(name="search")],
        ),
        "files": _fake_toolset(
            server_name="files",
            tools=[_fake_tool(name="search")],
        ),
    }
    _patch_build_toolset(monkeypatch, toolsets=toolsets)

    runtime = MCPRuntime(
        _config(
            servers={
                "docs": _server_def(),
                "files": _server_def(command="ls"),
            },
        )
    )

    with pytest.raises(MCPToolMetadataError):
        await runtime.list_tools()


async def test_list_tools_rejects_invalid_tool_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(
        server_name="docs",
        tools=[_fake_tool(name="")],
    )
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(MCPToolMetadataError):
        await runtime.list_tools()


async def test_list_tools_rejects_non_mapping_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool = SimpleNamespace(
        name="search", description="x", inputSchema=["not", "a", "map"]
    )
    toolset = _fake_toolset(server_name="docs", tools=[tool])
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(MCPToolSchemaError):
        await runtime.list_tools()


async def test_list_tools_propagates_cancelled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(
        server_name="docs",
        list_tools_side_effect=asyncio.CancelledError(),
    )
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(asyncio.CancelledError):
        await runtime.list_tools()


async def test_call_tool_routes_to_toolset_direct_call_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(server_name="docs")
    toolset.direct_call_tool = AsyncMock(
        return_value=SimpleNamespace(model_dump=lambda **_kwargs: {"content": "hit"})
    )
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    result = await runtime.call_tool("docs.search", {"query": "python"})

    assert isinstance(result, MCPToolResult)
    assert result.truncated is False
    toolset.direct_call_tool.assert_awaited_once_with("search", {"query": "python"})


async def test_call_tool_serializes_plain_dict_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(server_name="docs")
    toolset.direct_call_tool = AsyncMock(return_value={"content": "payload"})
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    result = await runtime.call_tool("docs.search", {})

    assert result.content == '{"content":"payload"}'
    assert result.truncated is False


async def test_call_tool_truncates_large_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    big = "x" * (mcp_module.DEFAULT_RESULT_LIMIT_BYTES + 100)
    toolset = _fake_toolset(server_name="docs")
    toolset.direct_call_tool = AsyncMock(return_value={"content": big})
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    result = await runtime.call_tool("docs.search", {})

    assert result.truncated is True
    assert len(result.content.encode("utf-8")) <= mcp_module.DEFAULT_RESULT_LIMIT_BYTES


async def test_call_tool_raises_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(server_name="docs")
    toolset.direct_call_tool = AsyncMock(side_effect=TimeoutError())
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(MCPToolTimeoutError):
        await runtime.call_tool("docs.search", {})


async def test_call_tool_raises_protocol_error_on_unknown_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(server_name="docs")
    toolset.direct_call_tool = AsyncMock(side_effect=RuntimeError("boom"))
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(MCPProtocolError):
        await runtime.call_tool("docs.search", {})


async def test_call_tool_raises_protocol_error_for_unqualified_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_build_toolset(monkeypatch)
    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(MCPProtocolError):
        await runtime.call_tool("search", {})


async def test_call_tool_raises_protocol_error_for_unknown_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_build_toolset(monkeypatch)
    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    with pytest.raises(MCPProtocolError):
        await runtime.call_tool("unknown.search", {})


async def test_call_tool_raises_configuration_error_when_disabled() -> None:
    runtime = MCPRuntime(_config(enabled=False))

    with pytest.raises(MCPConfigurationError):
        await runtime.call_tool("docs.search", {})


async def test_close_closes_each_toolset_client_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolsets = {
        "docs": _fake_toolset(server_name="docs"),
        "files": _fake_toolset(server_name="files"),
    }
    _patch_build_toolset(monkeypatch, toolsets=toolsets)

    runtime = MCPRuntime(
        _config(
            servers={
                "docs": _server_def(),
                "files": _server_def(command="ls"),
            },
        )
    )
    await runtime.toolsets()

    await runtime.close()
    await runtime.close()

    toolsets["docs"].client.close.assert_awaited_once()
    toolsets["files"].client.close.assert_awaited_once()


async def test_toolsets_raises_runtime_closed_after_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_build_toolset(monkeypatch)
    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))
    await runtime.close()

    with pytest.raises(MCPRuntimeClosedError):
        await runtime.toolsets()


async def test_close_swallows_per_toolset_close_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toolset = _fake_toolset(server_name="docs")
    toolset.client.close = AsyncMock(side_effect=RuntimeError("boom"))
    _patch_build_toolset(monkeypatch, toolsets={"docs": toolset})

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))
    await runtime.toolsets()

    await runtime.close()
    toolset.client.close.assert_awaited_once()


async def test_close_serializes_with_concurrent_toolset_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """close() shares the same lock as toolsets(); close waits for the build."""
    built: list[str] = []
    closed: list[str] = []

    def _build(name: str, _server: MCPServerDef) -> MagicMock:
        built.append(name)
        toolset = _fake_toolset(server_name=name)
        original_close = toolset.client.close

        async def _recording_close() -> None:
            closed.append(name)
            await original_close()

        toolset.client.close = _recording_close
        return toolset

    _patch_build_toolset(monkeypatch, builder=_build)

    runtime = MCPRuntime(_config(servers={"docs": _server_def()}))

    # Build the toolset first, then close. Both acquire the same lock
    # sequentially; close observes the populated _toolsets dict.
    toolsets = await runtime.toolsets()
    await runtime.close()

    assert built == ["docs"]
    assert closed == ["docs"]
    assert len(toolsets) == 1


def test_build_toolset_stdio_requires_command() -> None:
    server = MCPServerDef(transport="stdio", command=None)
    with pytest.raises(MCPConfigurationError):
        mcp_module._build_toolset("local", server)


def test_build_toolset_streamable_http_requires_url() -> None:
    server = MCPServerDef(transport="streamable_http", url=None)
    with pytest.raises(MCPConfigurationError):
        mcp_module._build_toolset("remote", server)


def test_headers_from_env_returns_none_when_name_is_empty() -> None:
    assert mcp_module._headers_from_env(None) is None


def test_headers_from_env_raises_when_env_var_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MCP_HEADERS_MISSING", raising=False)
    with pytest.raises(MCPConfigurationError):
        mcp_module._headers_from_env("MCP_HEADERS_MISSING")


def test_headers_from_env_raises_when_value_is_not_a_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_HEADERS_LIST", '["a", "b"]')
    try:
        with pytest.raises(MCPConfigurationError):
            mcp_module._headers_from_env("MCP_HEADERS_LIST")
    finally:
        monkeypatch.delenv("MCP_HEADERS_LIST", raising=False)


def test_headers_from_env_returns_mapping_when_well_formed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_HEADERS_OK", '{"Authorization": "Bearer t"}')
    try:
        headers = mcp_module._headers_from_env("MCP_HEADERS_OK")
        assert headers == {"Authorization": "Bearer t"}
    finally:
        monkeypatch.delenv("MCP_HEADERS_OK", raising=False)


def test_headers_from_env_rejects_non_string_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_HEADERS_BAD", '{"count": 5}')
    try:
        with pytest.raises(MCPConfigurationError):
            mcp_module._headers_from_env("MCP_HEADERS_BAD")
    finally:
        monkeypatch.delenv("MCP_HEADERS_BAD", raising=False)


def test_mcp_tool_descriptor_qualified_name_joins_server_and_tool() -> None:
    descriptor = MCPToolDescriptor(
        server_name="docs",
        name="search",
        description=None,
        input_schema={},
    )
    assert descriptor.qualified_name == "docs.search"


def test_mcp_tool_result_defaults_to_not_truncated() -> None:
    result = MCPToolResult(content="payload")
    assert result.truncated is False


def test_mcp_tool_result_accepts_truncated_flag() -> None:
    result = MCPToolResult(content="payload", truncated=True)
    assert result.truncated is True


def test_mcp_tool_descriptor_input_schema_is_frozen_by_caller() -> None:
    schema: dict[str, object] = {"type": "object"}
    descriptor = MCPToolDescriptor(
        server_name="docs",
        name="search",
        description=None,
        input_schema=cast("Mapping[str, object]", mcp_module.freeze_value(schema)),
    )
    assert descriptor.input_schema == {"type": "object"}


async def test_installation_exposes_pydantic_ai_mcp_toolset() -> None:
    from pydantic_ai.mcp import MCPToolset

    assert callable(MCPToolset)
