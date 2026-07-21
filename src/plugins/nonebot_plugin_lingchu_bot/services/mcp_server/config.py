"""Localstore-backed configuration for the inbound MCP server."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Final

from nonebot import require
from pydantic import BaseModel, ConfigDict, Field, field_validator

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ...database.toml_store import ensure_toml_dict_file_async, load_toml_dict_sync
from .administration import OAuthIdentityKind

if TYPE_CHECKING:
    from pathlib import Path

MCP_SERVER_CONFIG_FILENAME: Final = "mcp-server.toml"
MIN_CURSOR_SECRET_BYTES: Final = 32


class MCPServerConfigError(RuntimeError):
    """Reject an enabled server whose security configuration is incomplete."""


class MCPServerRouteError(ValueError):
    """Reject an invalid MCP mount route."""


class MCPServerConfig(BaseModel):
    """Strict disabled-by-default inbound MCP configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    route: str = "/mcp"
    issuer: str | None = None
    audience: str | None = None
    jwks_url: str | None = None
    identity_kind: OAuthIdentityKind = OAuthIdentityKind.SUBJECT
    cursor_secret_env: str | None = None
    read_rate_per_minute: int = Field(default=120, ge=1)
    send_rate_per_minute: int = Field(default=20, ge=1)
    conversation_send_rate_per_minute: int = Field(default=6, ge=1)
    principal_concurrency: int = Field(default=8, ge=1)
    conversation_write_concurrency: int = Field(default=2, ge=1)
    max_page_size: int = Field(default=200, ge=1, le=200)

    @field_validator("route")
    @classmethod
    def validate_route(cls, value: str) -> str:
        if not value.startswith("/") or value == "/":
            raise MCPServerRouteError
        return value.rstrip("/")

    def validate_enabled(self) -> None:
        """Fail closed when an enabled server lacks auth or cursor inputs."""
        if not self.enabled:
            return
        required = (self.issuer, self.audience, self.jwks_url, self.cursor_secret_env)
        if any(not value for value in required):
            raise MCPServerConfigError
        secret = os.environ.get(self.cursor_secret_env or "")
        if secret is None or len(secret.encode()) < MIN_CURSOR_SECRET_BYTES:
            raise MCPServerConfigError


def mcp_server_config_path() -> Path:
    return get_plugin_config_file(MCP_SERVER_CONFIG_FILENAME)


def load_mcp_server_config(path: Path | None = None) -> MCPServerConfig:
    target = path or mcp_server_config_path()
    config = MCPServerConfig.model_validate(load_toml_dict_sync(target))
    config.validate_enabled()
    return config


async def ensure_mcp_server_config_file_async(path: Path | None = None) -> Path:
    target = path or mcp_server_config_path()
    await ensure_toml_dict_file_async(
        target,
        MCPServerConfig().model_dump(mode="json"),
    )
    return target


__all__ = [
    "MCPServerConfig",
    "MCPServerConfigError",
    "ensure_mcp_server_config_file_async",
    "load_mcp_server_config",
    "mcp_server_config_path",
]
