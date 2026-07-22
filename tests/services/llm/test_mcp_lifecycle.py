from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import mcp_lifecycle


@pytest.fixture(autouse=True)
def reset_managed_mcp_agent() -> None:
    mcp_lifecycle._managed.agent = None
    mcp_lifecycle._managed.mcp = None


async def test_initialize_mcp_agent_runtime_builds_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MagicMock()
    mcp = MagicMock()
    builder = MagicMock(return_value=(agent, mcp))
    monkeypatch.setattr(mcp_lifecycle, "_build_mcp_agent_runtime", builder)

    assert await mcp_lifecycle.initialize_mcp_agent_runtime() is agent
    assert await mcp_lifecycle.initialize_mcp_agent_runtime() is agent
    builder.assert_called_once_with()


def test_get_mcp_agent_runtime_requires_initialization() -> None:
    with pytest.raises(mcp_lifecycle.MCPAgentRuntimeNotInitializedError):
        mcp_lifecycle.get_mcp_agent_runtime()


def test_get_mcp_agent_runtime_returns_managed_agent() -> None:
    agent = MagicMock()
    mcp_lifecycle._managed.agent = agent

    assert mcp_lifecycle.get_mcp_agent_runtime() is agent


def test_build_mcp_agent_runtime_wires_parent_runtime_and_policy_managers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = MagicMock()
    config.mcp = MagicMock()
    llm_runtime = MagicMock()
    mcp = MagicMock()
    agent = MagicMock()
    audit = MagicMock()
    confirmation = MagicMock()
    mcp_runtime_cls = MagicMock(return_value=mcp)
    agent_runtime_cls = MagicMock(return_value=agent)
    audit_cls = MagicMock(return_value=audit)
    confirmation_cls = MagicMock(return_value=confirmation)
    monkeypatch.setattr(
        mcp_lifecycle, "load_llm_runtime_config", MagicMock(return_value=config)
    )
    monkeypatch.setattr(
        mcp_lifecycle, "get_llm_runtime", MagicMock(return_value=llm_runtime)
    )
    monkeypatch.setattr(mcp_lifecycle, "MCPRuntime", mcp_runtime_cls)
    monkeypatch.setattr(mcp_lifecycle, "MCPAgentRuntime", agent_runtime_cls)
    monkeypatch.setattr(mcp_lifecycle, "MCPAuditRecorder", audit_cls)
    monkeypatch.setattr(mcp_lifecycle, "CriticalConfirmationManager", confirmation_cls)

    assert mcp_lifecycle._build_mcp_agent_runtime() == (agent, mcp)
    mcp_runtime_cls.assert_called_once_with(config.mcp)
    agent_runtime_cls.assert_called_once_with(
        llm_runtime,
        mcp,
        audit_recorder=audit,
        confirmation_manager=confirmation,
    )


async def test_reload_mcp_agent_runtime_publishes_candidate_and_closes_previous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = MagicMock()
    previous.close = AsyncMock()
    candidate = MagicMock()
    candidate_mcp = MagicMock()
    mcp_lifecycle._managed.mcp = previous
    monkeypatch.setattr(
        mcp_lifecycle,
        "_build_mcp_agent_runtime",
        MagicMock(return_value=(candidate, candidate_mcp)),
    )

    assert await mcp_lifecycle.reload_mcp_agent_runtime() is candidate
    assert mcp_lifecycle._managed.agent is candidate
    assert mcp_lifecycle._managed.mcp is candidate_mcp
    previous.close.assert_awaited_once_with()


async def test_shutdown_mcp_agent_runtime_detaches_and_closes_managed_mcp() -> None:
    agent = MagicMock()
    mcp = MagicMock()
    mcp.close = AsyncMock()
    mcp_lifecycle._managed.agent = agent
    mcp_lifecycle._managed.mcp = mcp

    await mcp_lifecycle.shutdown_mcp_agent_runtime()

    assert mcp_lifecycle._managed.agent is None
    assert mcp_lifecycle._managed.mcp is None
    mcp.close.assert_awaited_once_with()


async def test_shutdown_mcp_agent_runtime_allows_empty_state() -> None:
    await mcp_lifecycle.shutdown_mcp_agent_runtime()

    assert mcp_lifecycle._managed.agent is None
    assert mcp_lifecycle._managed.mcp is None
