"""Managed lifecycle for the explicit reviewed MCP Agent runtime."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .agent import MCPAgentRuntime
from .config import load_llm_runtime_config
from .mcp import MCPRuntime
from .mcp_audit import MCPAuditRecorder
from .mcp_confirmation import CriticalConfirmationManager
from .runtime import get_llm_runtime


@dataclass(slots=True)
class _ManagedMCPAgent:
    agent: MCPAgentRuntime | None = None
    mcp: MCPRuntime | None = None


_managed = _ManagedMCPAgent()
_lifecycle_lock = asyncio.Lock()


class MCPAgentRuntimeNotInitializedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("MCP Agent runtime is not initialized")


def _build_mcp_agent_runtime() -> tuple[MCPAgentRuntime, MCPRuntime]:
    """Build and validate a candidate without publishing it."""
    config = load_llm_runtime_config()
    mcp = MCPRuntime(config.mcp)
    agent = MCPAgentRuntime(
        get_llm_runtime(),
        mcp,
        audit_recorder=MCPAuditRecorder(),
        confirmation_manager=CriticalConfirmationManager(),
    )
    return agent, mcp


async def initialize_mcp_agent_runtime() -> MCPAgentRuntime:
    """Initialize the explicit MCP Agent once."""
    async with _lifecycle_lock:
        if _managed.agent is None:
            _managed.agent, _managed.mcp = _build_mcp_agent_runtime()
        return _managed.agent


def get_mcp_agent_runtime() -> MCPAgentRuntime:
    """Return the initialized explicit MCP Agent runtime."""
    if _managed.agent is None:
        raise MCPAgentRuntimeNotInitializedError
    return _managed.agent


async def reload_mcp_agent_runtime() -> MCPAgentRuntime:
    """Publish a validated candidate, then close the previous transports."""
    async with _lifecycle_lock:
        candidate, candidate_mcp = _build_mcp_agent_runtime()
        previous = _managed.mcp
        _managed.agent = candidate
        _managed.mcp = candidate_mcp
        if previous is not None:
            await previous.close()
        return candidate


async def shutdown_mcp_agent_runtime() -> None:
    """Detach the MCP Agent and close all owned transports."""
    async with _lifecycle_lock:
        managed = _managed.mcp
        _managed.agent = None
        _managed.mcp = None
        if managed is not None:
            await managed.close()


__all__ = [
    "MCPAgentRuntimeNotInitializedError",
    "get_mcp_agent_runtime",
    "initialize_mcp_agent_runtime",
    "reload_mcp_agent_runtime",
    "shutdown_mcp_agent_runtime",
]
