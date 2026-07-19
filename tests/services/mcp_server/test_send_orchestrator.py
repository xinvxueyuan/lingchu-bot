from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ConversationAddress,
    ErrorCode,
    OperationStatus,
    ResourceGrant,
    SendMessageRequest,
    SendMessageResult,
    ServicePrincipal,
    TextSegment,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.send_orchestrator import (
    IdempotencyLedger,
    SendMessageOrchestrator,
)

BOT = BotAddress("qq", "~onebot.v11", "default", "1")
CONVERSATION = ConversationAddress("group", "2")
PRINCIPAL = ServicePrincipal("p1", "test", enabled=True)
AUTH = object()
GRANT = ResourceGrant("g1", "p1", BOT, CONVERSATION, 1)


@dataclass
class Policy:
    calls: list[str]

    async def authorize_resource(self, authenticated: Any, **kwargs: Any) -> Any:
        self.calls.append("authorize")
        return type("Auth", (), {"authenticated": authenticated, "grant": GRANT})()

    async def recheck(self, authorization: Any) -> Any:
        self.calls.append("recheck")
        return authorization


@dataclass
class Audit:
    events: list[str]
    fail: bool = False

    async def record_pre_send(
        self, authorization: Any, payload: dict[str, Any]
    ) -> None:
        if self.fail:
            raise RuntimeError("audit down")
        self.events.append("pre")

    async def record_post_send(
        self, authorization: Any, payload: dict[str, Any], result: SendMessageResult
    ) -> None:
        self.events.append(f"post:{result.status}")


@pytest.mark.asyncio
async def test_send_orchestrator_orders_guards_and_replays_result() -> None:
    policy = Policy([])
    audit = Audit([])
    sent = 0

    class Action:
        async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
            nonlocal sent
            sent += 1
            return SendMessageResult("op-1", OperationStatus.SUCCEEDED, "m-1")

    orchestrator = SendMessageOrchestrator(
        action=Action(), policy=policy, audit=audit, ledger=IdempotencyLedger()
    )
    request = SendMessageRequest(BOT, CONVERSATION, (TextSegment("hi"),), "key")
    first = await orchestrator.send(AUTH, request)
    second = await orchestrator.send(AUTH, request)
    assert first == second
    assert sent == 1
    assert policy.calls == ["authorize", "recheck", "authorize"]
    assert audit.events == ["pre", "post:succeeded"]


@pytest.mark.asyncio
async def test_conflicting_idempotency_key_is_rejected() -> None:
    class Action:
        async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
            return SendMessageResult("op", OperationStatus.SUCCEEDED)

    orchestrator = SendMessageOrchestrator(
        action=Action(), policy=Policy([]), audit=Audit([]), ledger=IdempotencyLedger()
    )
    await orchestrator.send(
        AUTH, SendMessageRequest(BOT, CONVERSATION, (TextSegment("a"),), "key")
    )
    with pytest.raises(Exception) as exc:
        await orchestrator.send(
            AUTH, SendMessageRequest(BOT, CONVERSATION, (TextSegment("b"),), "key")
        )
    assert getattr(exc.value, "code", None) is ErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.asyncio
async def test_pre_audit_failure_is_fail_closed() -> None:
    class Action:
        async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
            pytest.fail("action must not run")

    orchestrator = SendMessageOrchestrator(
        action=Action(),
        policy=Policy([]),
        audit=Audit([], fail=True),
        ledger=IdempotencyLedger(),
    )
    with pytest.raises(Exception) as exc:
        await orchestrator.send(
            AUTH, SendMessageRequest(BOT, CONVERSATION, (TextSegment("a"),), "key")
        )
    assert getattr(exc.value, "code", None) is ErrorCode.AUDIT_UNAVAILABLE


@pytest.mark.asyncio
async def test_cancelled_send_is_uncertain_and_reraises() -> None:
    class Action:
        async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
            raise TimeoutError

    audit = Audit([])
    orchestrator = SendMessageOrchestrator(
        action=Action(), policy=Policy([]), audit=audit, ledger=IdempotencyLedger()
    )
    result = await orchestrator.send(
        AUTH, SendMessageRequest(BOT, CONVERSATION, (TextSegment("a"),), "key")
    )
    assert result.status is OperationStatus.UNCERTAIN
    assert audit.events == ["pre", "post:uncertain"]


@pytest.mark.asyncio
async def test_real_cancelled_error_finalizes_uncertain() -> None:
    class Action:
        async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
            raise asyncio.CancelledError

    orchestrator = SendMessageOrchestrator(
        action=Action(), policy=Policy([]), audit=Audit([]), ledger=IdempotencyLedger()
    )
    with pytest.raises(asyncio.CancelledError):
        await orchestrator.send(
            AUTH,
            SendMessageRequest(BOT, CONVERSATION, (TextSegment("a"),), "cancel"),
        )
    result = await orchestrator.send(
        AUTH,
        SendMessageRequest(BOT, CONVERSATION, (TextSegment("a"),), "cancel"),
    )
    assert result.status is OperationStatus.UNCERTAIN


@pytest.mark.asyncio
async def test_post_audit_failure_still_replays_result() -> None:
    class FailingPostAudit(Audit):
        async def record_post_send(
            self,
            authorization: Any,
            payload: dict[str, Any],
            result: SendMessageResult,
        ) -> None:
            raise RuntimeError("down")

    class Action:
        async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
            return SendMessageResult("op", OperationStatus.SUCCEEDED)

    audit = FailingPostAudit([])
    orchestrator = SendMessageOrchestrator(
        action=Action(),
        policy=Policy([]),
        audit=audit,
        ledger=IdempotencyLedger(),
    )
    request = SendMessageRequest(BOT, CONVERSATION, (TextSegment("a"),), "post")
    first = await orchestrator.send(AUTH, request)
    assert await orchestrator.send(AUTH, request) == first


@pytest.mark.asyncio
async def test_action_exception_is_stable_and_replayed() -> None:
    class Action:
        async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
            raise RuntimeError("secret")

    orchestrator = SendMessageOrchestrator(
        action=Action(),
        policy=Policy([]),
        audit=Audit([]),
        ledger=IdempotencyLedger(),
    )
    request = SendMessageRequest(BOT, CONVERSATION, (TextSegment("a"),), "failure")
    result = await orchestrator.send(AUTH, request)
    assert result.status is OperationStatus.FAILED
    assert await orchestrator.send(AUTH, request) == result
