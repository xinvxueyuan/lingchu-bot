from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from mcp.server.fastmcp import FastMCP
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server import (
    runtime as runtime_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.auth import (
    CatalogEntry,
    ProjectTokenVerifier,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.config import (
    MCPServerConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    CapabilityScope,
    ContractError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.runtime import (
    _segments,
    build_authenticated_server,
)


@pytest.fixture
def enabled_config(monkeypatch: pytest.MonkeyPatch) -> MCPServerConfig:
    monkeypatch.setenv(
        "LINGCHU_TEST_MCP_CURSOR_SECRET",
        "0123456789abcdef0123456789abcdef",
    )
    return MCPServerConfig(
        enabled=True,
        issuer="https://issuer.example",
        audience="https://resource.example/mcp",
        jwks_url="https://issuer.example/jwks",
        cursor_secret_env="LINGCHU_TEST_MCP_CURSOR_SECRET",
    )


@pytest.mark.asyncio
async def test_production_builder_exposes_authenticated_static_catalog(
    enabled_config: MCPServerConfig,
) -> None:
    server, _repository, _policy, _bots = build_authenticated_server(enabled_config)

    tools = await FastMCP.list_tools(server)
    resources = await server.list_resources()
    templates = await server.list_resource_templates()

    assert {tool.name for tool in tools} == {
        "bots.list",
        "messages.list_recent",
        "messages.send",
    }
    assert {str(resource.uri) for resource in resources} == {"lingchu://server/info"}
    assert {str(template.uriTemplate) for template in templates} == {
        "lingchu://bots/{platform_id}/{adapter_id}/{protocol_id}/{bot_id}"
    }
    assert isinstance(server._token_verifier, ProjectTokenVerifier)
    assert server.settings.auth is not None
    assert str(server.settings.auth.issuer_url) == "https://issuer.example/"
    assert (
        str(server.settings.auth.resource_server_url) == "https://resource.example/mcp"
    )
    assert server.settings.stateless_http is True


@pytest.mark.asyncio
async def test_tool_discovery_uses_current_authorization_filter(
    enabled_config: MCPServerConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server, _repository, policy, _bots = build_authenticated_server(enabled_config)
    authenticated = MagicMock()
    monkeypatch.setattr(
        policy,
        "authenticate",
        AsyncMock(return_value=authenticated),
    )
    monkeypatch.setattr(
        runtime_module,
        "_claims_from_context",
        MagicMock(),
    )
    catalog_filter = AsyncMock(
        return_value=(
            CatalogEntry(
                "bots.list",
                CapabilityScope.BOTS_LIST,
                resource_bound=False,
            ),
        )
    )
    monkeypatch.setattr(runtime_module, "filter_catalog", catalog_filter)

    tools = await server.list_tools()

    assert [tool.name for tool in tools] == ["bots.list"]
    catalog_filter.assert_awaited_once()
    assert server.settings.json_response is True
    assert server.settings.streamable_http_path == "/"


def test_production_builder_rejects_disabled_configuration() -> None:
    with pytest.raises(RuntimeError, match="disabled"):
        build_authenticated_server(MCPServerConfig())


@pytest.mark.parametrize(
    "segments",
    [
        [{"type": "text", "text": "hello", "url": "https://example.com/a.png"}],
        [{"type": "image", "text": "hello"}],
        [{"type": "audio", "url": "https://example.com/a.mp3"}],
    ],
)
def test_transport_segments_reject_ambiguous_or_unsupported_shapes(
    segments: list[dict[str, str]],
) -> None:
    with pytest.raises(ContractError):
        _segments(segments)
