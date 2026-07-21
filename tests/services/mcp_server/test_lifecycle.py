from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.lifecycle import (
    InboundMCPConfig,
    InboundMCPServer,
)


def test_disabled_server_does_not_build_or_mount() -> None:
    calls: list[str] = []
    server = InboundMCPServer(
        InboundMCPConfig(enabled=False),
        build_server=lambda: calls.append("build"),
        mount_app=lambda _path, _app: calls.append("mount"),
    )

    server.mount()

    assert calls == []


@pytest.mark.asyncio
async def test_enabled_server_mounts_once_and_manages_session_lifecycle() -> None:
    calls: list[str] = []

    class SessionManager:
        @asynccontextmanager
        async def run(self):
            calls.append("start")
            try:
                yield
            finally:
                calls.append("stop")

    class SDKServer:
        session_manager = SessionManager()

        def streamable_http_app(self) -> object:
            calls.append("app")
            return object()

    server = InboundMCPServer(
        InboundMCPConfig(enabled=True),
        build_server=SDKServer,
        mount_app=lambda path, _app: calls.append(f"mount:{path}"),
    )

    server.mount()
    server.mount()
    await server.start()
    await server.stop()

    assert calls == ["app", "mount:/mcp", "start", "stop"]


@pytest.mark.asyncio
async def test_enabled_start_requires_mount() -> None:
    server = InboundMCPServer(
        InboundMCPConfig(enabled=True),
        build_server=object,
        mount_app=lambda _path, _app: None,
    )

    with pytest.raises(RuntimeError):
        await server.start()
