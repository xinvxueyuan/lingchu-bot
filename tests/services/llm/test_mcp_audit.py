from __future__ import annotations

from unittest.mock import AsyncMock

from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import PermissionContext
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.agent import (
    MCPAgentRequest,
    MCPReviewDecision,
    MCPToolProposal,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.mcp_audit import (
    MCPAuditRecorder,
)


async def test_audit_records_hash_without_full_arguments() -> None:
    writer = AsyncMock()
    recorder = MCPAuditRecorder(writer=writer)

    recorded = await recorder.before_call(
        request=MCPAgentRequest(
            input="update",
            permission_context=PermissionContext(
                platform_id="qq",
                adapter_id="onebot.v11",
                account_id="bot",
                uid="user",
            ),
        ),
        proposal=MCPToolProposal("system.update", {"token": "secret-value"}),
        decision=MCPReviewDecision(
            "allow", "write_err", "requested secret-value token"
        ),
    )

    assert recorded is True
    assert writer.await_args is not None
    event = writer.await_args.args[0]
    assert event.api_name == "mcp.system.update"
    assert "secret-value" not in event.data_summary
    assert "arguments_sha256" in event.data_summary


async def test_audit_failure_returns_false() -> None:
    recorder = MCPAuditRecorder(writer=AsyncMock(side_effect=RuntimeError))

    recorded = await recorder.before_call(
        request=MCPAgentRequest(
            input="read",
            permission_context=PermissionContext(
                platform_id="qq", adapter_id=None, account_id=None
            ),
        ),
        proposal=MCPToolProposal("docs.read", {}),
        decision=MCPReviewDecision("allow", "read", "safe"),
    )

    assert recorded is False
