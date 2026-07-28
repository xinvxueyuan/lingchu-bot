"""Tests for the Pydantic AI Agent-backed MCPAgentRuntime."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import (
    MCPPermissionLevel,
    PermissionContext,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm import agent as agent_module
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.agent import (
    AuditRecorder,
    LLMResponder,
    MCPAgentPermissionError,
    MCPAgentRequest,
    MCPAgentResult,
    MCPAgentRuntime,
    MCPCaller,
    MCPReviewDecision,
    MCPToolCallOutcome,
    MCPToolProposal,
    MCPToolRound,
    PermissionResolver,
    _coerce_input,
    _default_permission_resolver,
    _extract_rounds,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    MCPConfig,
    MCPServerDef,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.mcp import (
    MCPToolDescriptor,
    MCPToolResult,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
    LLMProfile,
    LLMResponse,
    LLMUsage,
)


def _profile(name: str | None = None) -> LLMProfile:
    return LLMProfile(
        name=name or "main",
        backend="pydantic_ai",
        model="test:model",
        base_url=None,
        api_key=None,
        timeout=60.0,
        max_retries=2,
    )


def _response(
    *,
    text: str | None = None,
    output: tuple[object, ...] = (),
    raw: object = None,
    usage: LLMUsage | None = None,
) -> LLMResponse:
    return LLMResponse(
        text=text,
        output=output,
        usage=usage,
        request_id=None,
        model="test:model",
        backend="pydantic_ai",
        raw=raw,
    )


@dataclass
class FakeLLMResponder:
    responses: list[LLMResponse]
    selected_profile: LLMProfile | None = None

    def __post_init__(self) -> None:
        self.calls: list[tuple[object, str | None, Mapping[str, object]]] = []

    def profile(self, name: str | None = None) -> LLMProfile:
        if self.selected_profile is not None:
            return self.selected_profile
        return _profile(name)

    async def respond(
        self, request_input: object, /, *, profile: str | None = None, **params: object
    ) -> LLMResponse:
        self.calls.append((request_input, profile, params))
        return self.responses.pop(0) if self.responses else _response(text="fallback")


class FakeMCPCaller:
    def __init__(self, *, enabled: bool = True) -> None:
        self.config = MCPConfig(
            enabled=enabled,
            servers={"docs": MCPServerDef(transport="stdio", command="echo")},
        )
        self.toolsets_calls = 0
        self.list_tools_calls = 0
        self.call_tool_calls: list[tuple[str, Mapping[str, object]]] = []

    async def toolsets(self) -> tuple[Any, ...]:
        self.toolsets_calls += 1
        if not self.config.enabled:
            return ()
        return (SimpleNamespace(id="docs"),)

    async def list_tools(self) -> tuple[MCPToolDescriptor, ...]:
        self.list_tools_calls += 1
        return (
            MCPToolDescriptor(
                server_name="docs",
                name="search",
                description="Search documentation",
                input_schema={"type": "object"},
            ),
        )

    async def call_tool(
        self, qualified_name: str, arguments: Mapping[str, object], /
    ) -> MCPToolResult:
        self.call_tool_calls.append((qualified_name, arguments))
        return MCPToolResult(content='{"answer":"found"}')


def _context() -> PermissionContext:
    return PermissionContext(
        platform_id="qq", adapter_id="onebot.v11", account_id="bot", uid="user-1"
    )


async def _allow(_context: PermissionContext) -> MCPPermissionLevel:
    return "read"


async def _deny(_context: PermissionContext) -> None:
    return None


def _usage(
    *,
    input_tokens: int = 10,
    output_tokens: int = 20,
    total_tokens: int = 30,
    cache_read_tokens: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_read_tokens=cache_read_tokens,
    )


def _fake_agent_result(
    *,
    output: object = "done",
    run_id: str | None = "run-1",
    messages: Sequence[ModelMessage] | None = None,
    usage: SimpleNamespace | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        output=output,
        run_id=run_id,
        usage=usage or _usage(),
        all_messages=lambda: list(messages or []),
    )


def _tool_messages(
    *,
    tool_name: str = "docs.search",
    args: Mapping[str, object] | None = None,
    content: object = "hit",
) -> list[ModelMessage]:
    """Build a [ToolReturn, ToolCall] sequence the agent would emit."""
    call = ModelResponse(
        parts=[ToolCallPart(tool_name=tool_name, args=dict(args or {}))]
    )
    ret = ModelRequest(parts=[ToolReturnPart(tool_name=tool_name, content=content)])
    return [ret, call]


def _patch_build_agent(
    monkeypatch: pytest.MonkeyPatch,
    result: Any,
    *,
    run_side_effect: object | None = None,
) -> MagicMock:
    agent = MagicMock(name="pydantic_ai.Agent")
    if run_side_effect is not None:
        agent.run = AsyncMock(side_effect=run_side_effect)
    else:
        agent.run = AsyncMock(return_value=result)
    monkeypatch.setattr(
        MCPAgentRuntime,
        "_build_agent",
        staticmethod(lambda _profile, _toolsets: agent),
    )
    return agent


async def test_respond_returns_agent_result_with_response_and_rounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = _tool_messages(args={"query": "python"}, content="hit")
    fake_result = _fake_agent_result(output="The answer is found.", messages=messages)
    _patch_build_agent(monkeypatch, fake_result)

    llm = FakeLLMResponder([])
    mcp = FakeMCPCaller()
    runtime = MCPAgentRuntime(llm, mcp, permission_resolver=_allow)

    result = await runtime.respond(
        MCPAgentRequest(input="Find the answer", permission_context=_context())
    )

    assert isinstance(result, MCPAgentResult)
    assert result.response.text == "The answer is found."
    assert result.response.backend == "pydantic_ai"
    assert result.response.model == "test:model"
    assert result.response.request_id == "run-1"
    assert result.response.usage is not None
    assert result.response.usage.input_tokens == 10
    assert result.response.usage.output_tokens == 20
    assert result.response.usage.total_tokens == 30
    assert len(result.rounds) == 1
    round_ = result.rounds[0]
    assert round_.number == 1
    assert len(round_.calls) == 1
    call = round_.calls[0]
    assert call.status == "success"
    assert call.proposal.name == "docs.search"
    assert call.proposal.arguments == {"query": "python"}
    assert call.tool_result is not None
    assert call.tool_result.content == "hit"
    assert call.decision is None
    assert mcp.toolsets_calls == 1


async def test_respond_extracts_first_proposal_into_top_level_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = _tool_messages(args={"q": "x"}, content="hit")
    fake_result = _fake_agent_result(messages=messages)
    _patch_build_agent(monkeypatch, fake_result)

    runtime = MCPAgentRuntime(
        FakeLLMResponder([]), FakeMCPCaller(), permission_resolver=_allow
    )
    result = await runtime.respond(
        MCPAgentRequest(input="search", permission_context=_context())
    )

    assert result.proposal is not None
    assert result.proposal.name == "docs.search"
    assert result.tool_result is not None
    assert result.tool_result.content == "hit"
    assert result.decision is None


async def test_respond_raises_permission_error_when_resolver_returns_none() -> None:
    llm = FakeLLMResponder([])
    mcp = FakeMCPCaller()
    runtime = MCPAgentRuntime(llm, mcp, permission_resolver=_deny)

    with pytest.raises(MCPAgentPermissionError):
        await runtime.respond(
            MCPAgentRequest(input="search", permission_context=_context())
        )

    assert llm.calls == []
    assert mcp.toolsets_calls == 0


async def test_respond_falls_back_to_llm_when_agent_run_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fallback = _response(text="fallback response")
    llm = FakeLLMResponder([fallback])
    _patch_build_agent(
        monkeypatch, result=None, run_side_effect=RuntimeError("agent crashed")
    )

    runtime = MCPAgentRuntime(llm, FakeMCPCaller(), permission_resolver=_allow)
    result = await runtime.respond(
        MCPAgentRequest(input="search", permission_context=_context())
    )

    assert result.response.text == "fallback response"
    assert result.rounds == ()
    assert result.proposal is None
    assert result.tool_result is None
    assert len(llm.calls) == 1
    assert llm.calls[0][0] == "search"


async def test_respond_passes_string_input_as_user_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_result = _fake_agent_result(output="ok", messages=[])
    agent = _patch_build_agent(monkeypatch, fake_result)

    runtime = MCPAgentRuntime(
        FakeLLMResponder([]), FakeMCPCaller(), permission_resolver=_allow
    )
    await runtime.respond(MCPAgentRequest(input="hello", permission_context=_context()))

    agent.run.assert_awaited_once()
    call_kwargs = agent.run.await_args
    assert call_kwargs.args[0] == "hello"
    assert call_kwargs.kwargs["message_history"] is None


async def test_respond_builds_message_history_from_legacy_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_result = _fake_agent_result(output="ok", messages=[])
    agent = _patch_build_agent(monkeypatch, fake_result)

    runtime = MCPAgentRuntime(
        FakeLLMResponder([]), FakeMCPCaller(), permission_resolver=_allow
    )
    await runtime.respond(
        MCPAgentRequest(
            input=[
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "ok"},
                {"role": "user", "content": "second"},
            ],
            permission_context=_context(),
        )
    )

    call_kwargs = agent.run.await_args
    assert call_kwargs.args[0] == "second"
    history = call_kwargs.kwargs["message_history"]
    assert history is not None
    assert len(history) == 2
    # The assistant response is appended when seen; the prior user prompt is
    # folded into a ModelRequest only once a new user prompt supersedes it.
    assert isinstance(history[0], ModelResponse)
    assert isinstance(history[0].parts[0], TextPart)
    assert history[0].parts[0].content == "ok"
    assert isinstance(history[1], ModelRequest)
    assert isinstance(history[1].parts[0], UserPromptPart)
    assert history[1].parts[0].content == "first"


async def test_respond_prefixes_system_messages_to_user_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_result = _fake_agent_result(output="ok", messages=[])
    agent = _patch_build_agent(monkeypatch, fake_result)

    runtime = MCPAgentRuntime(
        FakeLLMResponder([]), FakeMCPCaller(), permission_resolver=_allow
    )
    await runtime.respond(
        MCPAgentRequest(
            input=[
                {"role": "system", "content": "Be terse"},
                {"role": "user", "content": "search"},
            ],
            permission_context=_context(),
        )
    )

    call_kwargs = agent.run.await_args
    assert call_kwargs.args[0] == "Be terse\n\nsearch"
    assert call_kwargs.kwargs["message_history"] is None


async def test_authorized_toolsets_returns_mcp_toolsets_for_any_permission() -> None:
    mcp = FakeMCPCaller()
    runtime = MCPAgentRuntime(FakeLLMResponder([]), mcp, permission_resolver=_allow)

    toolsets = await runtime._authorized_toolsets("read")

    assert mcp.toolsets_calls == 1
    assert len(toolsets) == 1


async def test_authorized_toolsets_returns_empty_when_mcp_disabled() -> None:
    mcp = FakeMCPCaller(enabled=False)
    runtime = MCPAgentRuntime(FakeLLMResponder([]), mcp, permission_resolver=_allow)

    toolsets = await runtime._authorized_toolsets("critical")

    assert toolsets == ()


def test_build_agent_constructs_pydantic_ai_agent_with_toolsets() -> None:
    profile = _profile()
    toolset: Any = SimpleNamespace(id="docs")
    agent = MCPAgentRuntime._build_agent(profile, [toolset])

    assert agent is not None
    assert hasattr(agent, "run")


def test_build_agent_passes_none_toolsets_when_empty() -> None:
    profile = _profile()
    agent = MCPAgentRuntime._build_agent(profile, None)

    assert agent is not None


def test_coerce_input_returns_string_unchanged_without_history() -> None:
    prompt, history = _coerce_input("search")

    assert prompt == "search"
    assert history is None


def test_coerce_input_returns_empty_for_unsupported_type() -> None:
    prompt, history = _coerce_input(42)

    assert prompt == ""
    assert history is None


def test_coerce_input_returns_empty_for_empty_list() -> None:
    prompt, history = _coerce_input([])

    assert prompt == ""
    assert history is None


def test_coerce_input_folds_message_list_into_prompt_and_history() -> None:
    prompt, history = _coerce_input([
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "second"},
    ])

    assert prompt == "second"
    assert history is not None
    assert len(history) == 2
    assert isinstance(history[0], ModelResponse)
    assert isinstance(history[1], ModelRequest)


def test_coerce_input_ignores_non_mapping_entries() -> None:
    prompt, history = _coerce_input(["raw string", {"role": "user", "content": "ok"}])

    assert prompt == "ok"
    assert history is None


def test_coerce_input_ignores_messages_with_non_string_fields() -> None:
    prompt, history = _coerce_input([
        {"role": 1, "content": "ok"},
        {"role": "user", "content": 5},
    ])

    assert prompt == ""
    assert history is None


def test_extract_rounds_returns_empty_when_no_tool_calls() -> None:
    messages: list[ModelMessage] = [
        ModelResponse(parts=[TextPart(content="hello")]),
    ]

    assert _extract_rounds(messages) == ()


def test_extract_rounds_returns_empty_when_no_responses() -> None:
    messages: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(content="hello")]),
    ]

    assert _extract_rounds(messages) == ()


def test_extract_rounds_builds_success_outcome_for_matched_return() -> None:
    messages = _tool_messages(tool_name="docs.search", args={"q": "x"}, content="hit")

    rounds = _extract_rounds(messages)

    assert len(rounds) == 1
    assert rounds[0].number == 1
    assert len(rounds[0].calls) == 1
    call = rounds[0].calls[0]
    assert call.status == "success"
    assert call.proposal.name == "docs.search"
    assert call.proposal.arguments == {"q": "x"}
    assert call.tool_result is not None
    assert call.tool_result.content == "hit"
    assert call.decision is None


def test_extract_rounds_reports_failed_when_no_matching_return() -> None:
    messages: list[ModelMessage] = [
        ModelResponse(parts=[ToolCallPart(tool_name="docs.search", args={})]),
    ]

    rounds = _extract_rounds(messages)

    assert len(rounds) == 1
    call = rounds[0].calls[0]
    assert call.status == "failed"
    assert call.tool_result is None


def test_extract_rounds_increments_round_number_for_multiple_responses() -> None:
    messages: list[ModelMessage] = [
        ModelResponse(parts=[ToolCallPart(tool_name="docs.search", args={})]),
        ModelRequest(parts=[ToolReturnPart(tool_name="docs.search", content="r1")]),
        ModelResponse(parts=[ToolCallPart(tool_name="docs.files", args={})]),
        ModelRequest(parts=[ToolReturnPart(tool_name="docs.files", content="r2")]),
    ]

    rounds = _extract_rounds(messages)

    assert [round_.number for round_ in rounds] == [1, 2]
    assert rounds[0].calls[0].proposal.name == "docs.search"
    assert rounds[1].calls[0].proposal.name == "docs.files"


def test_extract_rounds_handles_multiple_tool_calls_in_one_response() -> None:
    messages: list[ModelMessage] = [
        ModelResponse(
            parts=[
                ToolCallPart(tool_name="docs.search", args={}),
                ToolCallPart(tool_name="docs.fetch", args={}),
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(tool_name="docs.search", content="s"),
                ToolReturnPart(tool_name="docs.fetch", content="f"),
            ]
        ),
    ]

    rounds = _extract_rounds(messages)

    assert len(rounds) == 1
    assert len(rounds[0].calls) == 2
    statuses = {call.proposal.name: call.status for call in rounds[0].calls}
    assert statuses == {"docs.search": "success", "docs.fetch": "success"}


def test_extract_rounds_renders_non_string_return_content_as_json() -> None:
    messages: list[ModelMessage] = [
        ModelResponse(parts=[ToolCallPart(tool_name="docs.search", args={})]),
        ModelRequest(
            parts=[ToolReturnPart(tool_name="docs.search", content={"answer": "found"})]
        ),
    ]

    rounds = _extract_rounds(messages)

    assert rounds[0].calls[0].tool_result is not None
    assert rounds[0].calls[0].tool_result.content == '{"answer":"found"}'


def test_extract_rounds_renders_none_return_content_as_empty_string() -> None:
    messages: list[ModelMessage] = [
        ModelResponse(parts=[ToolCallPart(tool_name="docs.search", args={})]),
        ModelRequest(parts=[ToolReturnPart(tool_name="docs.search", content=None)]),
    ]

    rounds = _extract_rounds(messages)

    assert rounds[0].calls[0].tool_result is not None
    assert rounds[0].calls[0].tool_result.content == ""


class _FakeSessionContext:
    """Async context manager that yields a recorded MagicMock session."""

    def __init__(self, *, record: list[Any] | None = None) -> None:
        self._record = record

    async def __aenter__(self) -> Any:
        session = MagicMock(name="session")
        if self._record is not None:
            self._record.append(session)
        return session

    async def __aexit__(self, *_exc: object) -> None:
        return None


async def test_default_permission_resolver_opens_scoped_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions: list[Any] = []

    async def fake_resolve(
        session: Any, _context: PermissionContext
    ) -> MCPPermissionLevel:
        assert session is sessions[-1]
        return "critical"

    monkeypatch.setattr(
        agent_module, "get_session", lambda: _FakeSessionContext(record=sessions)
    )
    monkeypatch.setattr(agent_module, "_resolve_mcp_permission", fake_resolve)

    result = await _default_permission_resolver(_context())

    assert result == "critical"
    assert len(sessions) == 1


async def test_default_permission_resolver_propagates_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_resolve(
        _session: Any, _context: PermissionContext
    ) -> MCPPermissionLevel | None:
        return None

    monkeypatch.setattr(agent_module, "get_session", _FakeSessionContext)
    monkeypatch.setattr(agent_module, "_resolve_mcp_permission", fake_resolve)

    result = await _default_permission_resolver(_context())

    assert result is None


def test_mcp_agent_request_freezes_input() -> None:
    request = MCPAgentRequest(
        input={"query": ["a", "b"]}, permission_context=_context()
    )

    # Frozen input becomes immutable: MappingProxyType / tuple proxies.
    assert isinstance(request.input, Mapping)
    frozen_input = cast("Mapping[str, object]", request.input)
    query = frozen_input["query"]
    assert isinstance(query, tuple)
    assert query == ("a", "b")


def test_mcp_agent_request_accepts_string_input() -> None:
    request = MCPAgentRequest(input="search", permission_context=_context())

    assert request.input == "search"


def test_mcp_tool_proposal_freezes_arguments() -> None:
    proposal = MCPToolProposal(name="x", arguments={"a": [1, 2]})

    assert isinstance(proposal.arguments, Mapping)
    value = proposal.arguments["a"]
    assert isinstance(value, tuple)
    assert value == (1, 2)


def test_mcp_tool_proposal_rejects_non_dict_arguments() -> None:
    """Passing a non-dict-like value raises before freeze_value can run."""
    not_a_mapping: Any = "not a mapping"
    with pytest.raises((TypeError, ValueError)):
        MCPToolProposal(name="x", arguments=not_a_mapping)


def test_mcp_review_decision_construction() -> None:
    decision = MCPReviewDecision(decision="allow", risk="read", reason="safe")

    assert decision.decision == "allow"
    assert decision.risk == "read"
    assert decision.reason == "safe"


def test_mcp_tool_call_outcome_defaults() -> None:
    proposal = MCPToolProposal(name="x", arguments={})
    outcome = MCPToolCallOutcome(proposal=proposal, decision=None, status="success")

    assert outcome.proposal is proposal
    assert outcome.decision is None
    assert outcome.status == "success"
    assert outcome.tool_result is None
    assert outcome.confirmation is None
    assert outcome.authorization_context is None


def test_mcp_tool_call_outcome_accepts_full_fields() -> None:
    proposal = MCPToolProposal(name="x", arguments={})
    decision = MCPReviewDecision(decision="deny", risk="critical", reason="nope")
    tool_result = MCPToolResult(content="r")
    context = _context()
    outcome = MCPToolCallOutcome(
        proposal=proposal,
        decision=decision,
        status="denied",
        tool_result=tool_result,
        confirmation={"pending": True},
        authorization_context=context,
    )

    assert outcome.decision is decision
    assert outcome.status == "denied"
    assert outcome.tool_result is tool_result
    assert outcome.confirmation == {"pending": True}
    assert outcome.authorization_context is context


def test_mcp_tool_round_construction() -> None:
    proposal = MCPToolProposal(name="x", arguments={})
    outcome = MCPToolCallOutcome(proposal=proposal, decision=None, status="success")
    round_ = MCPToolRound(number=1, calls=(outcome,))

    assert round_.number == 1
    assert len(round_.calls) == 1
    assert round_.calls[0] is outcome


def test_mcp_agent_result_defaults() -> None:
    response = _response(text="ok")
    result = MCPAgentResult(response=response)

    assert result.response is response
    assert result.rounds == ()
    assert result.proposal is None
    assert result.decision is None
    assert result.tool_result is None


def test_llm_responder_protocol_accepts_fake() -> None:
    fake: LLMResponder = FakeLLMResponder([])
    assert callable(fake.profile)
    assert callable(fake.respond)


def test_mcp_caller_protocol_accepts_fake() -> None:
    fake: MCPCaller = FakeMCPCaller()
    assert hasattr(fake, "config")
    assert callable(fake.toolsets)
    assert callable(fake.list_tools)
    assert callable(fake.call_tool)


def test_audit_recorder_protocol_shape() -> None:
    class TrivialAudit:
        async def before_call(
            self,
            *,
            request: MCPAgentRequest,
            proposal: MCPToolProposal,
            decision: MCPReviewDecision,
        ) -> bool:
            return True

    audit: AuditRecorder = TrivialAudit()
    assert callable(audit.before_call)


def test_permission_resolver_protocol_accepts_async_callable() -> None:
    async def resolver(
        _context: PermissionContext,
    ) -> MCPPermissionLevel | None:
        return "read"

    resolver_ref: PermissionResolver = resolver
    assert callable(resolver_ref)


# Keep type-only imports referenced for runtime parity.
_ = (Any, Sequence)
