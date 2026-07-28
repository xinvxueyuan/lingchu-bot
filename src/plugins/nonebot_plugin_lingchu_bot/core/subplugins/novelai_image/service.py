"""NovelAI MCP client service managing the novelai-image-mcp subprocess."""

from __future__ import annotations

import base64
import os
from typing import TYPE_CHECKING, Any

from nonebot import get_driver, logger

from .config import NovelAIConfig, get_novelai_config

if TYPE_CHECKING:
    from fastmcp.client import Client
    from fastmcp.client.client import CallToolResult

# Module-level singleton
_client: NovelAIMCPClient | None = None


class NovelAIMCPClient:
    """Manages a fastmcp.client.Client stdio connection to novelai-image-mcp."""

    def __init__(self, config: NovelAIConfig) -> None:
        self._config = config
        self._client: Client | None = None

    def _build_env(self) -> dict[str, str]:
        """Build env vars for the MCP subprocess from config."""
        env = os.environ.copy()
        if self._config.token:
            env["NOVELAI_TOKEN"] = self._config.token
        if self._config.username:
            env["NOVELAI_USERNAME"] = self._config.username
        if self._config.password:
            env["NOVELAI_PASSWORD"] = self._config.password
        if self._config.output_dir:
            env["NOVELAI_OUTPUT_DIR"] = self._config.output_dir
        return env

    async def _ensure_client(self) -> Client:
        """Lazy-initialize the fastmcp client on first call."""
        if self._client is not None:
            return self._client
        from fastmcp.client import Client, StdioTransport

        transport = StdioTransport(
            command=self._config.mcp_command,
            args=list(self._config.mcp_args),
            env=self._build_env(),
        )
        self._client = Client(transport=transport, timeout=self._config.timeout)
        logger.info(
            "NovelAI MCP subprocess launching: {} {}",
            self._config.mcp_command,
            " ".join(self._config.mcp_args),
        )
        return self._client

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool and return decoded content.

        Returns bytes if the result contains ImageContent, str if TextContent.
        """
        client = await self._ensure_client()
        async with client:
            result: CallToolResult = await client.call_tool(name, arguments)
        return self._decode_result(result)

    def _decode_result(self, result: CallToolResult) -> Any:
        """Extract bytes (from ImageContent) or str (from TextContent) from result."""
        for block in result.content:
            block_type = getattr(block, "type", None)
            if block_type == "image":
                image_data = getattr(block, "data", None)
                if isinstance(image_data, str):
                    return base64.b64decode(image_data)
            elif block_type == "text":
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    return text
        return None

    async def shutdown(self) -> None:
        """Close the client and clean up the subprocess."""
        if self._client is not None:
            try:
                # fastmcp Client context manager handles subprocess cleanup on exit
                self._client = None
                logger.info("NovelAI MCP subprocess shut down")
            except Exception:
                logger.opt(colors=True).warning("NovelAI MCP shutdown error")


def get_novelai_mcp_client(config: NovelAIConfig | None = None) -> NovelAIMCPClient:
    """Get or create the module-level NovelAIMCPClient singleton."""
    global _client
    if _client is None:
        _client = NovelAIMCPClient(config or get_novelai_config())
    return _client


async def shutdown_novelai_mcp_client() -> None:
    """Shut down the module-level NovelAIMCPClient if it exists."""
    global _client
    if _client is not None:
        await _client.shutdown()
        _client = None


def _register_shutdown_hook() -> None:
    """Register shutdown on NoneBot driver shutdown."""
    try:
        driver = get_driver()
        driver.on_shutdown(shutdown_novelai_mcp_client)
    except Exception:
        logger.debug("NovelAI MCP shutdown hook registration skipped")


_register_shutdown_hook()


__all__ = [
    "NovelAIMCPClient",
    "get_novelai_mcp_client",
    "shutdown_novelai_mcp_client",
]
