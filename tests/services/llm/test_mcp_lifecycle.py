from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import mcp_lifecycle

if TYPE_CHECKING:
    from src.plugins.nonebot_plugin_lingchu_bot.services.llm.agent import (
        MCPAgentRuntime,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.services.llm.mcp import MCPRuntime


@dataclass
class _FakeMCP:
    closed: int = 0

    async def close(self) -> None:
        self.closed += 1


@pytest.fixture(autouse=True)
def _reset_managed_state() -> Iterator[None]:
    mcp_lifecycle._managed.agent = None
    mcp_lifecycle._managed.mcp = None
    yield
    mcp_lifecycle._managed.agent = None
    mcp_lifecycle._managed.mcp = None


async def test_reload_publishes_candidate_then_closes_previous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_mcp = _FakeMCP()
    previous_agent = object()
    candidate_mcp = _FakeMCP()
    candidate_agent = object()
    mcp_lifecycle._managed.agent = cast("MCPAgentRuntime", previous_agent)
    mcp_lifecycle._managed.mcp = cast("MCPRuntime", previous_mcp)
    monkeypatch.setattr(
        mcp_lifecycle,
        "_build_mcp_agent_runtime",
        lambda: (
            cast("MCPAgentRuntime", candidate_agent),
            cast("MCPRuntime", candidate_mcp),
        ),
    )

    result = await mcp_lifecycle.reload_mcp_agent_runtime()

    assert result is candidate_agent
    assert mcp_lifecycle.get_mcp_agent_runtime() is candidate_agent
    assert previous_mcp.closed == 1


async def test_failed_reload_preserves_previous_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_mcp = _FakeMCP()
    previous_agent = object()
    mcp_lifecycle._managed.agent = cast("MCPAgentRuntime", previous_agent)
    mcp_lifecycle._managed.mcp = cast("MCPRuntime", previous_mcp)

    def _fail() -> tuple[MCPAgentRuntime, MCPRuntime]:
        raise ValueError("invalid candidate")

    monkeypatch.setattr(mcp_lifecycle, "_build_mcp_agent_runtime", _fail)

    try:
        await mcp_lifecycle.reload_mcp_agent_runtime()
    except ValueError:
        pass
    else:
        raise AssertionError("invalid reload must fail")

    assert mcp_lifecycle.get_mcp_agent_runtime() is previous_agent
    assert previous_mcp.closed == 0


async def test_shutdown_detaches_agent_and_closes_transports() -> None:
    managed_mcp = _FakeMCP()
    mcp_lifecycle._managed.agent = cast("MCPAgentRuntime", object())
    mcp_lifecycle._managed.mcp = cast("MCPRuntime", managed_mcp)

    await mcp_lifecycle.shutdown_mcp_agent_runtime()

    assert managed_mcp.closed == 1
    try:
        mcp_lifecycle.get_mcp_agent_runtime()
    except RuntimeError:
        pass
    else:
        raise AssertionError("shutdown agent must be unavailable")
