from __future__ import annotations

import pytest
from pytest import MonkeyPatch

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.config import (
    MCPServerConfig,
    MCPServerConfigError,
)


def test_server_is_disabled_by_default() -> None:
    config = MCPServerConfig()

    config.validate_enabled()

    assert config.enabled is False
    assert config.route == "/mcp"
    assert config.read_rate_per_minute == 120
    assert config.send_rate_per_minute == 20


def test_enabled_server_rejects_missing_security_configuration() -> None:
    with pytest.raises(MCPServerConfigError):
        MCPServerConfig(enabled=True).validate_enabled()


def test_enabled_server_requires_strong_cursor_secret(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_CURSOR_SECRET", "short")
    config = MCPServerConfig(
        enabled=True,
        issuer="https://issuer.example",
        audience="https://bot.example/mcp",
        jwks_url="https://issuer.example/jwks.json",
        cursor_secret_env="MCP_CURSOR_SECRET",
    )

    with pytest.raises(MCPServerConfigError):
        config.validate_enabled()
