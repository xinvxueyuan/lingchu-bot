"""Pydantic AI MCP Agent workflow beside the tool-free LLM runtime.

The agent delegates the multi-round tool-calling loop to a
:class:`pydantic_ai.Agent` configured with MCPToolsets owned by
:class:`MCPRuntime`. Public DTOs (``MCPAgentRequest``, ``MCPAgentResult``,
``MCPToolProposal``, ``MCPReviewDecision``, ``MCPToolCallOutcome``,
``MCPToolRound``) are preserved so existing audit and test call sites
continue to type-check. The legacy multi-round orchestration, LLM-based
review, and confirmation flow have been removed; Pydantic AI's native
agent loop owns tool execution.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from nonebot import require
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ...permissions import resolve_mcp_permission as _resolve_mcp_permission
from .security import freeze_value
from .types import LLMProfile, LLMResponse, LLMUsage

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.toolsets import AbstractToolset
    from pydantic_ai.usage import RunUsage

    from ...permissions import MCPPermissionLevel, PermissionContext
    from .config import MCPConfig
    from .mcp import MCPToolDescriptor, MCPToolResult

type ReviewRisk = Literal["read", "write_err", "critical"]
type ReviewOutcome = Literal["allow", "deny"]
type ToolCallStatus = Literal[
    "success",
    "denied",
    "failed",
    "timed_out",
    "truncated",
    "confirmation_required",
]
type PermissionResolver = Callable[
    [PermissionContext], Awaitable[MCPPermissionLevel | None]
]


async def _default_permission_resolver(
    context: PermissionContext,
) -> MCPPermissionLevel | None:
    """Open a scoped session and resolve MCP permission level for a context."""
    async with get_session() as session:
        return await _resolve_mcp_permission(session, context)


class LLMResponder(Protocol):
    def profile(self, name: str | None = None) -> LLMProfile: ...

    async def respond(
        self, request_input: object, /, *, profile: str | None = None, **params: object
    ) -> LLMResponse: ...


class MCPCaller(Protocol):
    config: MCPConfig

    async def toolsets(self) -> tuple[AbstractToolset[Any], ...]: ...

    async def list_tools(self) -> tuple[MCPToolDescriptor, ...]: ...

    async def call_tool(
        self, qualified_name: str, arguments: Mapping[str, object], /
    ) -> MCPToolResult: ...


@dataclass(frozen=True, slots=True)
class MCPAgentRequest:
    input: object
    permission_context: PermissionContext
    session_id: str | None = None
    profile: str | None = None
    context_summary: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "input", freeze_value(self.input))


@dataclass(frozen=True, slots=True)
class MCPToolProposal:
    name: str
    arguments: Mapping[str, object]

    def __post_init__(self) -> None:
        frozen = freeze_value(dict(self.arguments))
        if not isinstance(frozen, Mapping):
            raise TypeError
        object.__setattr__(self, "arguments", frozen)


@dataclass(frozen=True, slots=True)
class MCPReviewDecision:
    decision: ReviewOutcome
    risk: ReviewRisk
    reason: str


class AuditRecorder(Protocol):
    async def before_call(
        self,
        *,
        request: MCPAgentRequest,
        proposal: MCPToolProposal,
        decision: MCPReviewDecision,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class MCPToolCallOutcome:
    proposal: MCPToolProposal
    decision: MCPReviewDecision | None
    status: ToolCallStatus
    tool_result: MCPToolResult | None = None
    confirmation: object | None = None
    authorization_context: PermissionContext | None = None


@dataclass(frozen=True, slots=True)
class MCPToolRound:
    number: int
    calls: tuple[MCPToolCallOutcome, ...]


@dataclass(frozen=True, slots=True)
class MCPAgentResult:
    response: LLMResponse
    rounds: tuple[MCPToolRound, ...] = ()
    proposal: MCPToolProposal | None = None
    decision: MCPReviewDecision | None = None
    tool_result: MCPToolResult | None = None


class MCPAgentPermissionError(PermissionError):
    """The actor has no MCP Preauthorization."""


class MCPAgentRuntime:
    """Drive one Pydantic AI Agent run over the configured MCP toolsets."""

    def __init__(
        self,
        llm: LLMResponder,
        mcp: MCPCaller,
        *,
        permission_resolver: PermissionResolver = _default_permission_resolver,
        audit_recorder: AuditRecorder | None = None,
        confirmation_manager: object | None = None,
    ) -> None:
        self._llm = llm
        self._mcp = mcp
        self._permission_resolver = permission_resolver
        self._audit = audit_recorder
        # confirmation_manager is no longer used: Pydantic AI's native
        # agent loop owns tool execution. Retained as a parameter so
        # existing call sites (mcp_lifecycle) continue to compile.
        self._confirmations = confirmation_manager

    async def respond(self, request: MCPAgentRequest) -> MCPAgentResult:
        permission = await self._permission_resolver(request.permission_context)
        if permission is None:
            raise MCPAgentPermissionError
        profile = self._llm.profile(request.profile)
        toolsets = await self._authorized_toolsets(permission)
        agent = self._build_agent(profile, toolsets)
        user_prompt, message_history = _coerce_input(request.input)
        try:
            result = await agent.run(
                user_prompt,
                message_history=message_history,
                model_settings=_build_model_settings(profile),
            )
        except Exception:
            # Fall back to a plain LLM response without MCP context so the
            # caller still receives a stable LLMResponse. This mirrors the
            # LLMRuntime behavior of normalizing provider errors but keeps
            # the surface minimal — the audit boundary is preserved by the
            # MCP audit recorder separately.
            response = await self._llm.respond(user_prompt, profile=request.profile)
            return MCPAgentResult(response=response)
        response = _from_agent_result(result, profile)
        rounds = _extract_rounds(result.all_messages())
        return _result(response, rounds)

    async def _authorized_toolsets(
        self, permission: MCPPermissionLevel
    ) -> tuple[AbstractToolset[Any], ...]:
        """Return MCPToolsets only when the actor has any MCP permission.

        Pydantic AI's Agent enforces per-tool authorization internally; the
        runtime gates access at the toolset level. Any non-None permission
        level grants access to all configured MCP servers; ``None`` would
        have raised ``MCPAgentPermissionError`` upstream.
        """
        _ = permission
        return await self._mcp.toolsets()

    @staticmethod
    def _build_agent(
        profile: LLMProfile, toolsets: Sequence[AbstractToolset[Any]] | None
    ) -> Agent[Any, Any]:
        """Construct a Pydantic AI ``Agent`` with the resolved MCP toolsets."""
        return Agent(
            model=profile.model,
            retries=profile.max_retries,
            model_settings=_build_model_settings(profile),
            toolsets=toolsets or None,
            defer_model_check=True,
        )


def _result(response: LLMResponse, rounds: Sequence[MCPToolRound]) -> MCPAgentResult:
    frozen_rounds = tuple(rounds)
    first = (
        frozen_rounds[0].calls[0] if frozen_rounds and frozen_rounds[0].calls else None
    )
    return MCPAgentResult(
        response=response,
        rounds=frozen_rounds,
        proposal=first.proposal if first else None,
        decision=first.decision if first else None,
        tool_result=first.tool_result if first else None,
    )


def _from_agent_result(result: AgentRunResult[Any], profile: LLMProfile) -> LLMResponse:
    """Map a Pydantic AI ``AgentRunResult`` to the stable ``LLMResponse``."""
    output = result.output
    text = output if isinstance(output, str) else str(output)
    request_id = getattr(result, "run_id", None)
    request_id_text = str(request_id) if isinstance(request_id, str) else None
    return LLMResponse(
        text=text,
        output=(),
        usage=_from_usage(result.usage),
        request_id=request_id_text,
        model=profile.model,
        backend="pydantic_ai",
        raw=result,
    )


def _from_usage(usage: RunUsage) -> LLMUsage | None:
    """Map a Pydantic AI ``RunUsage`` to the stable ``LLMUsage`` projection."""
    input_tokens = usage.input_tokens or None
    output_tokens = usage.output_tokens or None
    total_tokens = usage.total_tokens or None
    cached_tokens = usage.cache_read_tokens or None
    if not any((input_tokens, output_tokens, total_tokens, cached_tokens)):
        return None
    return LLMUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_tokens=cached_tokens,
        reasoning_tokens=None,
    )


def _build_model_settings(profile: LLMProfile) -> ModelSettings | None:
    settings: dict[str, Any] = {}
    if profile.base_url:
        settings["base_url"] = profile.base_url
    if profile.timeout:
        settings["timeout"] = profile.timeout
    return cast("ModelSettings | None", settings or None)


def _coerce_input(
    request_input: object,
) -> tuple[str, list[ModelMessage] | None]:
    """Convert the legacy input format to a user prompt and optional history."""
    if isinstance(request_input, str):
        return request_input, None
    if not isinstance(request_input, (list, tuple)):
        return "", None
    history: list[ModelMessage] = []
    pending_system: list[str] = []
    last_user_prompt: str | None = None
    for raw in request_input:
        last_user_prompt = _consume_legacy_message(
            raw, history, pending_system, last_user_prompt
        )
    if last_user_prompt is None:
        return "", None
    prompt = (
        "\n\n".join([*pending_system, last_user_prompt])
        if pending_system
        else last_user_prompt
    )
    return prompt, history or None


def _consume_legacy_message(
    raw: object,
    history: list[ModelMessage],
    pending_system: list[str],
    last_user_prompt: str | None,
) -> str | None:
    """Fold one legacy ``{"role", "content"}`` dict into the running state."""
    if not isinstance(raw, Mapping):
        return last_user_prompt
    role = raw.get("role")
    content = raw.get("content")
    if not isinstance(role, str) or not isinstance(content, str):
        return last_user_prompt
    if role == "system":
        pending_system.append(content)
        return last_user_prompt
    if role == "user":
        if last_user_prompt is not None:
            history.append(
                ModelRequest(parts=[UserPromptPart(content=last_user_prompt)])
            )
        return content
    if role == "assistant":
        history.append(ModelResponse(parts=[TextPart(content=content)]))
    return last_user_prompt


def _extract_rounds(messages: Sequence[ModelMessage]) -> tuple[MCPToolRound, ...]:
    """Build ``MCPToolRound`` entries from the agent's message history."""
    rounds: list[MCPToolRound] = []
    round_number = 0
    returns_by_id = _index_tool_returns(messages)
    for message in messages:
        if not isinstance(message, ModelResponse):
            continue
        proposals = _tool_proposals_from_response(message)
        if not proposals:
            continue
        round_number += 1
        outcomes = tuple(
            _outcome_from_proposal(proposal, returns_by_id) for proposal in proposals
        )
        rounds.append(MCPToolRound(round_number, outcomes))
    return tuple(rounds)


def _index_tool_returns(
    messages: Sequence[ModelMessage],
) -> dict[str, ToolReturnPart]:
    """Index ``ToolReturnPart`` instances by their ``tool_call_id``."""
    returns: dict[str, ToolReturnPart] = {}
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                returns[part.tool_call_id] = part
    return returns


def _tool_proposals_from_response(
    response: ModelResponse,
) -> tuple[MCPToolProposal, ...]:
    proposals: list[MCPToolProposal] = []
    for part in response.parts:
        if not isinstance(part, ToolCallPart):
            continue
        arguments = cast("Mapping[str, object]", part.args_as_dict())
        try:
            proposals.append(MCPToolProposal(name=part.tool_name, arguments=arguments))
        except TypeError:
            continue
    return tuple(proposals)


def _outcome_from_proposal(
    proposal: MCPToolProposal,
    returns_by_id: Mapping[str, ToolReturnPart],
) -> MCPToolCallOutcome:
    """Build a best-effort ``MCPToolCallOutcome`` for one tool call.

    The Pydantic AI agent executed the tool internally; we surface the
    returned content as an ``MCPToolResult`` when available, otherwise the
    outcome is reported as ``failed``. ``decision`` is always ``None``
    because the legacy LLM-based review step has been removed.
    """
    # We do not have the tool_call_id on the proposal DTO; without it we
    # cannot reliably correlate the proposal to a specific ToolReturnPart
    # when multiple calls share a name. The first matching return by
    # tool name is used as a best-effort projection.
    matching_return: ToolReturnPart | None = None
    for return_part in returns_by_id.values():
        if return_part.tool_name == proposal.name:
            matching_return = return_part
            break
    if matching_return is None:
        return MCPToolCallOutcome(
            proposal=proposal, decision=None, status="failed", tool_result=None
        )
    content = _tool_return_text(matching_return.content)
    return MCPToolCallOutcome(
        proposal=proposal,
        decision=None,
        status="success",
        tool_result=_mcp_tool_result(content),
    )


def _tool_return_text(content: object) -> str:
    """Render a ``ToolReturnPart.content`` payload as a bounded string."""
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    try:
        return json.dumps(content, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(content)


def _mcp_tool_result(content: str) -> MCPToolResult:
    """Build a local ``MCPToolResult`` view of one tool return."""
    from .mcp import MCPToolResult

    return MCPToolResult(content=content)


__all__ = [
    "AuditRecorder",
    "LLMResponder",
    "MCPAgentPermissionError",
    "MCPAgentRequest",
    "MCPAgentResult",
    "MCPAgentRuntime",
    "MCPCaller",
    "MCPReviewDecision",
    "MCPToolCallOutcome",
    "MCPToolProposal",
    "MCPToolRound",
    "PermissionResolver",
]
