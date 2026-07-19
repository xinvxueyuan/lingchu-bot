"""Static MCP v1 catalog backed only by injected authorized operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

type Operation = Callable[..., Awaitable[Any]]


def build_catalog_server(
    *,
    list_bots: Operation,
    list_recent_messages: Operation,
    send_message: Operation,
    server_info: Operation,
    bot_info: Operation,
) -> Any:
    """Build the approved static Tools/Resources catalog for SDK v1."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "Lingchu Bot",
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
    )
    server.tool(name="bots.list")(list_bots)
    server.tool(name="messages.list_recent")(list_recent_messages)
    server.tool(name="messages.send")(send_message)
    server.resource("lingchu://server/info")(server_info)
    server.resource("lingchu://bots/{platform}/{adapter}/{bot_id}")(bot_info)
    return server


__all__ = ["build_catalog_server"]
