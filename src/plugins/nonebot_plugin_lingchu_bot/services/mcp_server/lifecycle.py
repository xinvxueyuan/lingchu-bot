"""Lifecycle and ASGI mounting for the inbound MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class InboundMCPNotMountedError(RuntimeError):
    """Reject startup before the ASGI sub-application is mounted."""


@dataclass(frozen=True, slots=True)
class InboundMCPConfig:
    """Minimal transport settings for the disabled-by-default server."""

    enabled: bool = False
    route: str = "/mcp"


class InboundMCPServer:
    """Build, mount, and lifecycle-manage one MCP ASGI application."""

    def __init__(
        self,
        config: InboundMCPConfig,
        *,
        build_server: Callable[[], Any] | None = None,
        mount_app: Callable[[str, Any], None] | None = None,
    ) -> None:
        self.config = config
        self._build_server = build_server or _build_fastmcp
        self._mount_app = mount_app or _mount_nonebot_app
        self._server: Any | None = None
        self._mounted = False
        self._session_context: Any | None = None

    def mount(self) -> None:
        """Mount the configured server once, or do nothing when disabled."""
        if not self.config.enabled or self._mounted:
            return
        self._server = self._build_server()
        app = self._server.streamable_http_app()
        self._mount_app(self.config.route, app)
        self._mounted = True

    async def start(self) -> None:
        """Start the SDK session manager after the host app is mounted."""
        if not self.config.enabled:
            return
        if not self._mounted or self._server is None:
            raise InboundMCPNotMountedError
        self._session_context = self._server.session_manager.run()
        await self._session_context.__aenter__()

    async def stop(self) -> None:
        """Stop the session manager and release its host-owned context."""
        context = self._session_context
        self._session_context = None
        if context is not None:
            await context.__aexit__(None, None, None)


def _build_fastmcp() -> Any:
    from mcp.server.fastmcp import FastMCP

    return FastMCP(
        "Lingchu Bot",
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
    )


def _mount_nonebot_app(route: str, app: Any) -> None:
    import nonebot

    host = nonebot.get_app()
    host.mount(route, app)


__all__ = ["InboundMCPConfig", "InboundMCPServer"]
