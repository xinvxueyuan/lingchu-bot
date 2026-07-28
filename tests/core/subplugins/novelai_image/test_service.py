"""Tests for the NovelAI MCP client service."""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import service
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.config import (
    NovelAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.service import (
    NovelAIMCPClient,
)


@pytest.fixture(autouse=True)
def reset_singleton() -> Any:
    """Reset the module-level singleton before and after each test."""
    service._client = None
    yield
    service._client = None


@pytest.fixture
def full_config() -> NovelAIConfig:
    """Config with all credentials populated."""
    return NovelAIConfig(
        token="tok-123",
        username="user-abc",
        password="pass-xyz",
        output_dir="/tmp/novelai-out",
    )


# ---------------------------------------------------------------------------
# _build_env
# ---------------------------------------------------------------------------


class TestBuildEnv:
    def test_with_all_credentials(self, full_config: NovelAIConfig) -> None:
        client = NovelAIMCPClient(full_config)
        env = client._build_env()
        assert env["NOVELAI_TOKEN"] == "tok-123"
        assert env["NOVELAI_USERNAME"] == "user-abc"
        assert env["NOVELAI_PASSWORD"] == "pass-xyz"
        assert env["NOVELAI_OUTPUT_DIR"] == "/tmp/novelai-out"

    def test_without_credentials(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        env = client._build_env()
        assert "NOVELAI_TOKEN" not in env
        assert "NOVELAI_USERNAME" not in env
        assert "NOVELAI_PASSWORD" not in env
        assert "NOVELAI_OUTPUT_DIR" not in env

    def test_preserves_existing_env(self, full_config: NovelAIConfig) -> None:
        client = NovelAIMCPClient(full_config)
        env = client._build_env()
        # os.environ is copied, so PATH etc. should be present
        assert "PATH" in env


# ---------------------------------------------------------------------------
# _decode_result
# ---------------------------------------------------------------------------


class TestDecodeResult:
    def test_image_content(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        raw = b"\x89PNG\r\n\x1a\n"
        block = Mock(type="image", data=base64.b64encode(raw).decode())
        result = Mock(content=[block])
        assert client._decode_result(result) == raw

    def test_text_content(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        block = Mock(type="text", text="suggested tags")
        result = Mock(content=[block])
        assert client._decode_result(result) == "suggested tags"

    def test_empty_content(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        result = Mock(content=[])
        assert client._decode_result(result) is None

    def test_unknown_block_type(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        block = Mock(type="resource", data="whatever")
        result = Mock(content=[block])
        assert client._decode_result(result) is None

    def test_image_with_non_string_data(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        block = Mock(type="image", data=b"raw-bytes-not-b64")
        result = Mock(content=[block])
        assert client._decode_result(result) is None

    def test_text_with_non_string_text(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        block = Mock(type="text", text=42)
        result = Mock(content=[block])
        assert client._decode_result(result) is None

    def test_first_matching_block_wins(self) -> None:
        client = NovelAIMCPClient(NovelAIConfig())
        raw = b"\x89PNG"
        image_block = Mock(type="image", data=base64.b64encode(raw).decode())
        text_block = Mock(type="text", text="ignored")
        result = Mock(content=[image_block, text_block])
        assert client._decode_result(result) == raw


# ---------------------------------------------------------------------------
# _ensure_client
# ---------------------------------------------------------------------------


class TestEnsureClient:
    async def test_lazy_init(self, full_config: NovelAIConfig) -> None:
        client = NovelAIMCPClient(full_config)
        mock_mcp = Mock()
        with (
            patch("fastmcp.client.Client", return_value=mock_mcp) as mock_cls,
            patch("fastmcp.client.StdioTransport") as mock_transport_cls,
        ):
            result = await client._ensure_client()
        assert result is mock_mcp
        assert client._client is mock_mcp
        mock_transport_cls.assert_called_once()
        mock_cls.assert_called_once()

    async def test_reuses_existing(self, full_config: NovelAIConfig) -> None:
        client = NovelAIMCPClient(full_config)
        existing = Mock()
        client._client = existing
        with (
            patch("fastmcp.client.Client") as mock_cls,
            patch("fastmcp.client.StdioTransport") as mock_transport_cls,
        ):
            result = await client._ensure_client()
        assert result is existing
        mock_cls.assert_not_called()
        mock_transport_cls.assert_not_called()


# ---------------------------------------------------------------------------
# call_tool
# ---------------------------------------------------------------------------


class TestCallTool:
    async def test_call_tool_invokes_mcp_client(
        self, full_config: NovelAIConfig
    ) -> None:
        client = NovelAIMCPClient(full_config)
        raw = b"\x89PNG"
        decoded_result = Mock(
            content=[Mock(type="image", data=base64.b64encode(raw).decode())]
        )
        mock_mcp = AsyncMock()
        mock_mcp.call_tool.return_value = decoded_result
        client._client = mock_mcp
        result = await client.call_tool("generate_image", {"prompt": "cat"})
        assert result == raw
        mock_mcp.call_tool.assert_called_once_with("generate_image", {"prompt": "cat"})

    async def test_call_tool_ensures_client(self, full_config: NovelAIConfig) -> None:
        client = NovelAIMCPClient(full_config)
        mock_mcp = AsyncMock()
        mock_mcp.call_tool.return_value = Mock(content=[])
        with patch.object(client, "_ensure_client", return_value=mock_mcp):
            await client.call_tool("get_subscription", {})
        mock_mcp.call_tool.assert_called_once_with("get_subscription", {})


# ---------------------------------------------------------------------------
# shutdown
# ---------------------------------------------------------------------------


class TestShutdown:
    async def test_with_active_client(self, full_config: NovelAIConfig) -> None:
        client = NovelAIMCPClient(full_config)
        client._client = Mock()
        await client.shutdown()
        assert client._client is None

    async def test_without_client(self, full_config: NovelAIConfig) -> None:
        client = NovelAIMCPClient(full_config)
        await client.shutdown()
        assert client._client is None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_client_returns_singleton(self, full_config: NovelAIConfig) -> None:
        c1 = service.get_novelai_mcp_client(full_config)
        c2 = service.get_novelai_mcp_client(full_config)
        assert c1 is c2

    def test_get_client_uses_default_config_when_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When config is None, the factory falls back to get_novelai_config()."""
        sentinel = NovelAIConfig(token="fallback-tok")
        monkeypatch.setattr(service, "get_novelai_config", lambda: sentinel)
        c = service.get_novelai_mcp_client(None)
        assert c._config is sentinel

    async def test_shutdown_novelai_mcp_client_clears_singleton(
        self, full_config: NovelAIConfig
    ) -> None:
        c = service.get_novelai_mcp_client(full_config)
        c._client = Mock()
        await service.shutdown_novelai_mcp_client()
        assert service._client is None

    async def test_shutdown_when_no_singleton(self) -> None:
        """Calling shutdown with no active singleton is a no-op."""
        await service.shutdown_novelai_mcp_client()
        assert service._client is None
