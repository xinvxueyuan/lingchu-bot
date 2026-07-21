from __future__ import annotations

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.catalog import (
    build_catalog_server,
)


async def _operation() -> dict[str, object]:
    return {}


async def _bot_info(platform: str, adapter: str, bot_id: str) -> dict[str, object]:
    return {"platform": platform, "adapter": adapter, "bot_id": bot_id}


@pytest.mark.asyncio
async def test_catalog_contains_only_approved_capabilities() -> None:
    server = build_catalog_server(
        list_bots=_operation,
        list_recent_messages=_operation,
        send_message=_operation,
        server_info=_operation,
        bot_info=_bot_info,
    )

    tools = await server.list_tools()
    resources = await server.list_resources()
    prompts = await server.list_prompts()

    assert {tool.name for tool in tools} == {
        "bots.list",
        "messages.list_recent",
        "messages.send",
    }
    assert {str(resource.uri) for resource in resources} == {
        "lingchu://server/info",
    }
    assert prompts == []


def test_catalog_uses_stateless_json_streamable_http() -> None:
    server = build_catalog_server(
        list_bots=_operation,
        list_recent_messages=_operation,
        send_message=_operation,
        server_info=_operation,
        bot_info=_bot_info,
    )

    app = server.streamable_http_app()

    assert server.settings.stateless_http is True
    assert server.settings.json_response is True
    assert server.settings.streamable_http_path == "/"
    assert app is not None
