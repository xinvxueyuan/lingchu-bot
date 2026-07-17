"""Durable audit adapter for reviewed MCP calls."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import logging
from typing import TYPE_CHECKING, Protocol

from ...repositories import message_store
from .security import thaw_value

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from .agent import MCPAgentRequest, MCPReviewDecision, MCPToolProposal

logger = logging.getLogger(__name__)
SUMMARY_LIMIT = 500


class AuditWriter(Protocol):
    def __call__(self, event: message_store.AuditEvent) -> Awaitable[object]: ...


@dataclass(frozen=True, slots=True)
class MCPAuditRecorder:
    """Translate MCP decisions into the existing durable audit boundary."""

    writer: AuditWriter = message_store.record_api_call

    async def before_call(
        self,
        *,
        request: MCPAgentRequest,
        proposal: MCPToolProposal,
        decision: MCPReviewDecision,
    ) -> bool:
        """Persist a bounded pre-execution record, returning durability status."""
        context = request.permission_context
        arguments = _canonical_json(proposal.arguments)
        summary = _summary({
            "arguments_sha256": sha256(arguments.encode()).hexdigest(),
            "decision": decision.decision,
            "reason_sha256": sha256(decision.reason.encode()).hexdigest(),
            "risk": decision.risk,
            "scope_id": context.scope_id,
            "scope_type": context.scope_type,
            "uid": context.uid,
        })
        try:
            await self.writer(
                message_store.AuditEvent(
                    platform_id=context.platform_id,
                    adapter_id=context.adapter_id or "unknown",
                    protocol_id=None,
                    bot_id=context.account_id or "unknown",
                    api_name=f"mcp.{proposal.name}",
                    data_summary=summary,
                    result_summary="pre_execution",
                    exception_summary=None,
                    audit_type="mcp_tool_call",
                )
            )
        except Exception:
            logger.exception(
                "Failed to persist MCP pre-execution audit for %s", proposal.name
            )
            return False
        return True


def _canonical_json(value: object) -> str:
    return json.dumps(
        thaw_value(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )


def _summary(value: object) -> str:
    text = _canonical_json(value)
    return text if len(text) <= SUMMARY_LIMIT else text[:SUMMARY_LIMIT]


__all__ = ["MCPAuditRecorder"]
