"""Fail-closed orchestration for externally initiated message sends."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import hashlib
import json
from time import monotonic
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from .auth import AuthorizationError
from .contracts import (
    BotAddress,
    CapabilityScope,
    ContractError,
    ConversationAddress,
    ErrorCode,
    OperationStatus,
    SendMessageRequest,
    SendMessageResult,
    TextSegment,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .auth import AuthenticatedPrincipal, ResourceAuthorization


class SendAction(Protocol):
    async def send_message(self, request: SendMessageRequest) -> SendMessageResult: ...


class SendPolicy(Protocol):
    async def authorize_resource(
        self,
        authenticated: AuthenticatedPrincipal,
        *,
        capability: CapabilityScope,
        bot: BotAddress,
        conversation: ConversationAddress,
    ) -> ResourceAuthorization: ...
    async def recheck(
        self, authorization: ResourceAuthorization
    ) -> ResourceAuthorization: ...


class SendAudit(Protocol):
    async def record_pre_send(
        self, authorization: ResourceAuthorization, payload: dict[str, Any]
    ) -> None: ...
    async def record_post_send(
        self,
        authorization: ResourceAuthorization,
        payload: dict[str, Any],
        result: SendMessageResult,
    ) -> None: ...


@dataclass
class _Entry:
    fingerprint: str
    result: SendMessageResult | None = None
    in_progress: bool = True


class InvalidSendLimitsError(ValueError):
    """Reject non-positive externally configured send limits."""


@dataclass(frozen=True, slots=True)
class SendLimits:
    """Configured send rate and concurrency boundaries."""

    principal_rate_per_minute: int = 20
    conversation_rate_per_minute: int = 6
    principal_concurrency: int = 8
    conversation_concurrency: int = 2

    def __post_init__(self) -> None:
        if min(asdict(self).values()) < 1:
            raise InvalidSendLimitsError


class IdempotencyLedger:
    """In-memory ledger seam; production can replace it with an ORM repository."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], _Entry] = {}
        self._lock = asyncio.Lock()

    async def reserve(
        self, principal: str, tool: str, key: str, fingerprint: str, operation_id: str
    ) -> tuple[str, SendMessageResult | None]:
        async with self._lock:
            entry = self._entries.get((principal, tool, key))
            if entry is not None:
                if entry.fingerprint != fingerprint:
                    raise ContractError(
                        ErrorCode.IDEMPOTENCY_CONFLICT,
                        "idempotency key conflicts with an existing request",
                    )
                if entry.in_progress:
                    return "in_progress", None
                return "replay", entry.result
            self._entries[(principal, tool, key)] = _Entry(fingerprint)
            return operation_id, None

    async def finalize(
        self, principal: str, tool: str, key: str, result: SendMessageResult
    ) -> None:
        async with self._lock:
            entry = self._entries.get((principal, tool, key))
            if entry is not None:
                entry.result = result
                entry.in_progress = False

    async def abort(
        self, principal: str, tool: str, key: str, result: SendMessageResult
    ) -> None:
        await self.finalize(principal, tool, key, result)


class _Limiter:
    def __init__(
        self,
        limit: int,
        *,
        window: float = 60.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.limit, self.window, self.clock = limit, window, clock
        self.events: dict[str, list[float]] = {}
        self.lock = asyncio.Lock()

    async def acquire(self, key: str) -> None:
        async with self.lock:
            now = self.clock()
            values = [
                value for value in self.events.get(key, []) if now - value < self.window
            ]
            if len(values) >= self.limit:
                raise ContractError(ErrorCode.RATE_LIMITED, "send rate limit exceeded")
            values.append(now)
            self.events[key] = values


def _fingerprint(request: SendMessageRequest) -> str:
    body = [
        ("text", segment.text)
        if isinstance(segment, TextSegment)
        else ("image", segment.url)
        for segment in request.segments
    ]
    return hashlib.sha256(
        json.dumps(
            {
                "bot": asdict(request.bot),
                "conversation": asdict(request.conversation),
                "segments": body,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()


class SendMessageOrchestrator:
    """Authorize, reserve, audit, limit, execute, and finalize one send."""

    def __init__(
        self,
        *,
        action: SendAction,
        policy: SendPolicy,
        audit: SendAudit,
        ledger: IdempotencyLedger,
        limits: SendLimits | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._action, self._policy, self._audit, self._ledger = (
            action,
            policy,
            audit,
            ledger,
        )
        send_limits = limits or SendLimits()
        self._principal_limiter = _Limiter(
            send_limits.principal_rate_per_minute,
            clock=clock,
        )
        self._conversation_limiter = _Limiter(
            send_limits.conversation_rate_per_minute,
            clock=clock,
        )
        self._principal_concurrency = send_limits.principal_concurrency
        self._conversation_concurrency = send_limits.conversation_concurrency
        self._principal_sem: dict[str, asyncio.Semaphore] = {}
        self._conversation_sem: dict[str, asyncio.Semaphore] = {}
        self._max_concurrency_keys = 1024

    def _semaphore(
        self, mapping: dict[str, asyncio.Semaphore], key: str, limit: int
    ) -> asyncio.Semaphore:
        semaphore = mapping.get(key)
        if semaphore is None:
            if len(mapping) >= self._max_concurrency_keys:
                mapping.pop(next(iter(mapping)))
            semaphore = mapping[key] = asyncio.Semaphore(limit)
        return semaphore

    async def send(
        self, authenticated: AuthenticatedPrincipal, request: SendMessageRequest
    ) -> SendMessageResult:
        authorization = await self._policy.authorize_resource(
            authenticated,
            capability=CapabilityScope.MESSAGES_SEND,
            bot=request.bot,
            conversation=request.conversation,
        )
        principal_id = authorization.grant.principal_id
        operation_id = str(uuid4())
        state, replay = await self._ledger.reserve(
            principal_id,
            "messages.send",
            request.idempotency_key,
            _fingerprint(request),
            operation_id,
        )
        if state in {"replay", "in_progress"}:
            return replay or SendMessageResult(
                operation_id, OperationStatus.IN_PROGRESS
            )
        try:
            await self._principal_limiter.acquire(principal_id)
            conversation_key = f"{principal_id}:{request.bot}:{request.conversation}"
            await self._conversation_limiter.acquire(conversation_key)
        except (ContractError, asyncio.CancelledError):
            rejected = SendMessageResult(
                operation_id,
                OperationStatus.REJECTED,
                error_code=ErrorCode.RATE_LIMITED,
            )
            await asyncio.shield(
                self._ledger.abort(
                    principal_id, "messages.send", request.idempotency_key, rejected
                )
            )
            raise
        principal_sem = self._semaphore(
            self._principal_sem, principal_id, self._principal_concurrency
        )
        conversation_sem = self._semaphore(
            self._conversation_sem,
            conversation_key,
            self._conversation_concurrency,
        )
        async with principal_sem, conversation_sem:
            payload = {
                "operation_id": operation_id,
                "principal_id": principal_id,
                "grant_id": authorization.grant.grant_id,
                "tool": "messages.send",
                "bot": request.bot.bot_id,
                "conversation": request.conversation.conversation_id,
            }
            try:
                await self._audit.record_pre_send(authorization, payload)
            except (RuntimeError, OSError, ValueError) as exc:
                rejected = SendMessageResult(
                    operation_id,
                    OperationStatus.REJECTED,
                    error_code=ErrorCode.AUDIT_UNAVAILABLE,
                )
                await self._ledger.finalize(
                    principal_id, "messages.send", request.idempotency_key, rejected
                )
                raise ContractError(
                    ErrorCode.AUDIT_UNAVAILABLE, "send audit unavailable"
                ) from exc
            try:
                authorization = await self._policy.recheck(authorization)
                result = await self._action.send_message(request)
            except AuthorizationError:
                result = SendMessageResult(
                    operation_id,
                    OperationStatus.REJECTED,
                    error_code=ErrorCode.AUTHORIZATION_DENIED,
                )
            except asyncio.CancelledError:
                uncertain = SendMessageResult(
                    operation_id,
                    OperationStatus.UNCERTAIN,
                    error_code=ErrorCode.PLATFORM_FAILED,
                )
                await asyncio.shield(
                    self._finalize(
                        authorization, payload, principal_id, request, uncertain
                    )
                )
                raise
            except (TimeoutError, ConnectionError, OSError):
                result = SendMessageResult(
                    operation_id,
                    OperationStatus.UNCERTAIN,
                    error_code=ErrorCode.PLATFORM_FAILED,
                )
            except (RuntimeError, ValueError):
                result = SendMessageResult(
                    operation_id,
                    OperationStatus.FAILED,
                    error_code=ErrorCode.PLATFORM_FAILED,
                )
            await self._finalize(authorization, payload, principal_id, request, result)
            return result

    async def _finalize(
        self,
        authorization: ResourceAuthorization,
        payload: dict[str, Any],
        principal_id: str,
        request: SendMessageRequest,
        result: SendMessageResult,
    ) -> None:
        try:
            await self._audit.record_post_send(authorization, payload, result)
        except (RuntimeError, OSError, ValueError):
            pass
        finally:
            await self._ledger.finalize(
                principal_id, "messages.send", request.idempotency_key, result
            )
