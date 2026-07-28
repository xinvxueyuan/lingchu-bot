"""Managed lifecycle and stable response facade for the Pydantic AI agent."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
import hashlib
import os
import threading
import time
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic_ai import Agent
from pydantic_ai.exceptions import AgentRunError, ModelAPIError, ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from .capabilities import invalidate_capability_cache
from .config import LLMRuntimeConfig, load_llm_runtime_config
from .errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMDependencyError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from .observability import LLMCallRecord, StructuredLLMObserver
from .security import CONTROL_PLANE_KEYS, sanitize_message
from .types import LLMEvent, LLMProfile, LLMResponse, LLMUsage

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.usage import RunUsage

type RuntimeState = Literal["NEW", "RUNNING", "CLOSING", "CLOSED"]

HTTP_RATE_LIMITED = 429


@dataclass(frozen=True, slots=True)
class _Observation:
    request_id: str | None = None
    usage: LLMUsage | None = None
    sdk_metadata: object | None = None


class _RuntimeClosingError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("LLM runtime is closing or closed")


class _ForeignLoopError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("LLM runtime is bound to another active event loop")


class _WrongBackendError(LLMConfigurationError):
    def __init__(self, actual: str, expected: str) -> None:
        super().__init__(f"profile backend is {actual}, not {expected}")


class _ControlPlaneParameterError(LLMConfigurationError):
    def __init__(self) -> None:
        super().__init__(
            "control-plane parameters are not accepted by stable LLM calls"
        )


def _fingerprint(secret: str | None) -> str:
    # SHA-256 produces a stable cache key for LLM profile lookup by API key;
    # this is NOT password storage. argon2/bcrypt are unsuitable because their
    # random salts make them non-deterministic and unusable as dict keys.
    # CodeQL py/weak-sensitive-data-hashing flagged this as false positive
    # (dismissed: alert #2).
    value = secret.encode("utf-8", errors="replace") if secret else b""
    return hashlib.sha256(value).hexdigest()


def _error_status(error: LLMError) -> str:
    categories: tuple[tuple[type[LLMError], str], ...] = (
        (LLMDependencyError, "dependency_error"),
        (LLMConfigurationError, "configuration_error"),
        (LLMAuthenticationError, "authentication_error"),
        (LLMRateLimitError, "rate_limit_error"),
        (LLMTimeoutError, "timeout_error"),
        (LLMConnectionError, "connection_error"),
    )
    for error_type, status in categories:
        if isinstance(error, error_type):
            return status
    return "provider_error"


def _normalized_error(exc: Exception, profile: LLMProfile) -> LLMError:
    metadata: dict[str, object] = {
        "backend": "pydantic_ai",
        "model": profile.model,
    }
    if isinstance(exc, ModelHTTPError):
        status = exc.status_code
        metadata["status_code"] = status
        metadata["request_id"] = None
        if status in {401, 403}:
            return LLMAuthenticationError(
                "LLM provider call failed", **cast("Any", metadata)
            )
        if status == HTTP_RATE_LIMITED:
            metadata["retryable"] = True
            return LLMRateLimitError(
                "LLM provider call failed", **cast("Any", metadata)
            )
        if status in {408, 504}:
            metadata["retryable"] = True
            return LLMTimeoutError("LLM provider call failed", **cast("Any", metadata))
        return LLMProviderError("LLM provider call failed", **cast("Any", metadata))
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        metadata["retryable"] = True
        return LLMTimeoutError("LLM provider call failed", **cast("Any", metadata))
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return LLMDependencyError(
            "Pydantic AI agent unavailable; install 'pydantic-ai' and configure "
            "[pydantic-ai] in llm.toml",
            **cast("Any", metadata),
        )
    if isinstance(exc, (ModelAPIError, AgentRunError)):
        return LLMProviderError("LLM provider call failed", **cast("Any", metadata))
    exc_type_name = type(exc).__name__.casefold()
    if "connect" in exc_type_name or "connection" in exc_type_name:
        metadata["retryable"] = True
        return LLMConnectionError("LLM provider call failed", **cast("Any", metadata))
    return LLMProviderError("LLM provider call failed", **cast("Any", metadata))


def _coerce_input(
    input: object,
) -> tuple[str, list[ModelMessage] | None]:
    """Convert the legacy input format to a Pydantic AI user prompt and history.

    Pydantic AI's ``Agent.run`` accepts a plain string prompt (or a sequence
    of ``UserContent`` parts, which we do not produce here). Legacy callers
    (notably ``contracts.py``) historically passed a list of
    ``{"role", "content"}`` dicts. The last user message becomes
    ``user_prompt`` and prior messages become ``message_history`` using
    Pydantic AI message objects. System messages are prepended to the
    resolved user prompt to preserve instructions without exercising the
    Agent's ``system_prompt`` parameter.
    """
    if type(input) is str:
        return input, None
    if not isinstance(input, (list, tuple)):
        return "", None
    history: list[ModelMessage] = []
    pending_system: list[str] = []
    last_user_prompt: str | None = None
    for raw in input:
        if not isinstance(raw, Mapping):
            continue
        role = raw.get("role")
        content = raw.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        if role == "system":
            pending_system.append(content)
            continue
        if role == "user":
            if last_user_prompt is not None:
                history.append(
                    ModelRequest(parts=[UserPromptPart(content=last_user_prompt)])
                )
            last_user_prompt = content
            continue
        if role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
    if last_user_prompt is None:
        return "", None
    prompt = (
        "\n\n".join([*pending_system, last_user_prompt])
        if pending_system
        else last_user_prompt
    )
    return prompt, history or None


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


def _from_agent_result(result: AgentRunResult[Any], profile: LLMProfile) -> LLMResponse:
    """Map a Pydantic AI ``AgentRunResult`` to the stable ``LLMResponse``."""
    output = result.output
    text = output if isinstance(output, str) else str(output)
    request_id = getattr(result, "run_id", None)
    request_id_text = (
        sanitize_message(request_id) if isinstance(request_id, str) else None
    )
    return LLMResponse(
        text=text,
        output=(),
        usage=_from_usage(result.usage),
        request_id=request_id_text,
        model=profile.model,
        backend="pydantic_ai",
        raw=result,
    )


def _build_model_settings(
    profile: LLMProfile, params: Mapping[str, object]
) -> dict[str, Any]:
    """Build Pydantic AI ``model_settings`` from profile and caller params."""
    settings: dict[str, Any] = {}
    if profile.base_url:
        settings["base_url"] = profile.base_url
    if profile.timeout:
        settings["timeout"] = profile.timeout
    settings.update({
        key: value for key, value in params.items() if key not in CONTROL_PLANE_KEYS
    })
    return settings


class LLMRuntime:
    """Own resolved profiles, Pydantic AI agents, and their shutdown lifecycle."""

    def __init__(
        self,
        config: LLMRuntimeConfig,
        *,
        generation: int = 0,
        observer: StructuredLLMObserver | None = None,
    ) -> None:
        self.config = config
        self.generation = generation
        self._observer = observer or StructuredLLMObserver(
            enabled=bool(config.observability.enabled)
        )
        self._profiles: dict[tuple[str, int, str], LLMProfile] = {}
        self._agents: dict[tuple[str, int, str], Agent[Any, Any]] = {}
        self._lock = threading.RLock()
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._close_task: asyncio.Task[None] | None = None
        self.state: RuntimeState = "NEW"

    def _bind_async_loop(self) -> asyncio.AbstractEventLoop:
        """Bind async lifecycle work to one live loop at a time."""
        current = asyncio.get_running_loop()
        with self._lock:
            bound = self._async_loop
            if bound is None or bound.is_closed():
                self._async_loop = current
            elif bound is not current:
                raise _ForeignLoopError
        return current

    def _ensure_running(self) -> None:
        if self.state in {"CLOSING", "CLOSED"}:
            raise _RuntimeClosingError
        if self.state == "NEW":
            self.state = "RUNNING"

    def profile(self, name: str | None = None) -> LLMProfile:
        """Resolve and cache one named profile from ``PydanticAIConfig``."""
        with self._lock:
            self._ensure_running()
            pydantic_ai_cfg = self.config.pydantic_ai
            api_key = (
                os.environ.get(pydantic_ai_cfg.api_key_env)
                if pydantic_ai_cfg.api_key_env
                else None
            )
            resolved = LLMProfile(
                name=name or "default",
                backend="pydantic_ai",
                model=pydantic_ai_cfg.model,
                base_url=pydantic_ai_cfg.base_url,
                api_key=api_key,
                timeout=pydantic_ai_cfg.timeout,
                max_retries=2,
            )
            key = (resolved.name, self.generation, _fingerprint(resolved.api_key))
            cached = self._profiles.get(key)
            if cached is None:
                stale = [
                    existing
                    for existing in self._profiles
                    if existing[:2] == (resolved.name, self.generation)
                ]
                for existing in stale:
                    self._profiles.pop(existing, None)
                self._profiles[key] = resolved
                cached = resolved
            return cached

    def _agent(self, name: str | None = None) -> Agent[Any, Any]:
        """Return a cached Pydantic AI ``Agent`` for the resolved profile."""
        with self._lock:
            profile = self.profile(name)
            key = (profile.name, self.generation, _fingerprint(profile.api_key))
            cached = self._agents.get(key)
            if cached is None:
                stale = [
                    existing
                    for existing in self._agents
                    if existing[:2] == (profile.name, self.generation)
                ]
                for existing in stale:
                    self._agents.pop(existing, None)
                cached = self._build_agent(profile)
                self._agents[key] = cached
            return cached

    @staticmethod
    def _build_agent(profile: LLMProfile) -> Agent[Any, Any]:
        """Construct a Pydantic AI ``Agent`` from a resolved profile.

        ``defer_model_check=True`` defers provider/api-key validation until the
        first ``run``/``run_stream`` call so that runtime construction does not
        crash when an env var (e.g. ``OPENAI_API_KEY``) is provisioned later in
        deployment. Pydantic AI reads provider credentials from the env vars
        declared by ``PydanticAIConfig.api_key_env`` at call time.
        """
        model_settings: dict[str, Any] = {}
        if profile.base_url:
            model_settings["base_url"] = profile.base_url
        return Agent(
            model=profile.model,
            retries=profile.max_retries,
            model_settings=cast("ModelSettings | None", model_settings or None),
            defer_model_check=True,
        )

    def openai(self, name: str | None = None) -> object:
        """Deprecated: OpenAI backend removed. Always raises."""
        _ = name
        raise _WrongBackendError("pydantic_ai", "openai")

    def litellm(self, name: str | None = None) -> object:
        """Deprecated: LiteLLM backend removed. Always raises."""
        _ = name
        raise _WrongBackendError("pydantic_ai", "litellm")

    async def respond(
        self,
        input: object,
        *,
        profile: str | None = None,
        **params: object,
    ) -> LLMResponse:
        """Generate one normalized response through Pydantic AI."""
        self._bind_async_loop()
        rejected = CONTROL_PLANE_KEYS.intersection(params)
        if rejected:
            raise _ControlPlaneParameterError
        selected = self.profile(profile)
        started = time.perf_counter()
        try:
            agent = self._agent(selected.name)
            user_prompt, message_history = _coerce_input(input)
            model_settings = _build_model_settings(selected, params)
            result = await agent.run(
                user_prompt,
                message_history=message_history,
                model_settings=cast("ModelSettings | None", model_settings or None),
            )
            response = _from_agent_result(result, selected)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error = _normalized_error(exc, selected)
            self._emit(
                selected,
                started,
                _error_status(error),
                observation=_Observation(sdk_metadata=exc),
            )
            raise error from exc
        self._emit(
            selected,
            started,
            "success",
            observation=_Observation(
                request_id=response.request_id,
                usage=response.usage,
                sdk_metadata=result,
            ),
        )
        return response

    async def stream(
        self,
        input: object,
        *,
        profile: str | None = None,
        **params: object,
    ) -> AsyncIterator[LLMEvent]:
        """Yield a stable projection of one Pydantic AI stream."""
        self._bind_async_loop()
        rejected = CONTROL_PLANE_KEYS.intersection(params)
        if rejected:
            raise _ControlPlaneParameterError
        selected = self.profile(profile)
        started = time.perf_counter()
        try:
            agent = self._agent(selected.name)
            user_prompt, message_history = _coerce_input(input)
            model_settings = _build_model_settings(selected, params)
            yield LLMEvent(type="started", data=selected, raw=None)
            async with agent.run_stream(
                user_prompt,
                message_history=message_history,
                model_settings=cast("ModelSettings | None", model_settings or None),
            ) as result:
                async for text_delta in result.stream_text(delta=True):
                    yield LLMEvent(type="text_delta", data=text_delta, raw=None)
                final_text = await result.get_output()
                final_usage = result.usage
                final_response = LLMResponse(
                    text=(
                        final_text if isinstance(final_text, str) else str(final_text)
                    ),
                    output=(),
                    usage=_from_usage(final_usage),
                    request_id=(
                        sanitize_message(result.run_id)
                        if isinstance(result.run_id, str)
                        else None
                    ),
                    model=selected.model,
                    backend="pydantic_ai",
                    raw=result,
                )
                yield LLMEvent(type="completed", data=final_response, raw=result)
                self._emit(
                    selected,
                    started,
                    "success",
                    operation="stream",
                    observation=_Observation(
                        request_id=final_response.request_id,
                        usage=final_response.usage,
                        sdk_metadata=result,
                    ),
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error = _normalized_error(exc, selected)
            self._emit(
                selected,
                started,
                _error_status(error),
                operation="stream",
                observation=_Observation(sdk_metadata=exc),
            )
            raise error from exc

    def _emit(
        self,
        profile: LLMProfile,
        started: float,
        status: str,
        *,
        operation: str = "respond",
        observation: _Observation | None = None,
    ) -> None:
        details = observation or _Observation()
        try:
            self._observer.emit(
                LLMCallRecord(
                    operation=operation,
                    profile=profile.name,
                    backend="pydantic_ai",
                    model=profile.model,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    status=status,
                    request_id=details.request_id,
                    usage=details.usage,
                    retry_count=None,
                    fallback_count=None,
                )
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return

    async def _close_owned(self) -> None:
        """Release cached agents and profiles; agents own no explicit close."""
        with self._lock:
            self._agents.clear()
            self._profiles.clear()
            self.state = "CLOSED"

    async def close(self) -> None:
        """Close every owned resource once, continuing after individual failures."""
        with self._lock:
            if self.state == "CLOSED":
                return
        self._bind_async_loop()
        with self._lock:
            self.state = "CLOSING"
            if self._close_task is None or self._close_task.done():
                self._close_task = asyncio.create_task(self._close_owned())
            task = self._close_task
        await asyncio.shield(task)


@dataclass(slots=True)
class _ManagedRuntimeState:
    runtime: LLMRuntime | None = None
    generation: int = 0
    shutting_down: bool = False


@dataclass(slots=True)
class _LifecycleTicket:
    active: bool = True
    claimed: bool = False


class _LifecycleCoordinator:
    """Serialize async control-plane work across threads and event loops."""

    _POLL_INTERVAL = 0.01

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._busy = False

    def _claim(self, ticket: _LifecycleTicket) -> bool:
        with self._condition:
            if self._busy or not ticket.active:
                return False
            self._busy = True
            ticket.claimed = True
            return True

    def _cancel(self, ticket: _LifecycleTicket) -> None:
        with self._condition:
            ticket.active = False
            if ticket.claimed:
                ticket.claimed = False
                self._busy = False
            self._condition.notify_all()

    async def acquire(self) -> _LifecycleTicket:
        """Claim the coordinator without binding it to the caller's event loop."""
        ticket = _LifecycleTicket()
        try:
            while ticket.active:
                if self._claim(ticket):
                    return ticket
                await asyncio.sleep(self._POLL_INTERVAL)
        except BaseException:
            self._cancel(ticket)
            raise
        raise asyncio.CancelledError

    def release(self, ticket: _LifecycleTicket) -> None:
        with self._condition:
            if not ticket.claimed:
                return
            ticket.claimed = False
            ticket.active = False
            self._busy = False
            self._condition.notify_all()


_managed_state = _ManagedRuntimeState()
_managed_runtime_lock = threading.RLock()
_lifecycle_coordinator = _LifecycleCoordinator()


async def _finish_cleanup_before_cancellation(cleanup: Any) -> None:
    """Keep lifecycle serialization until owned cleanup finishes."""
    task = asyncio.ensure_future(cleanup)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    task.result()
    if cancelled:
        raise asyncio.CancelledError


def _build_managed_runtime(*, generation: int) -> LLMRuntime:
    """Build and structurally validate a candidate without publishing it."""
    config = load_llm_runtime_config()
    return LLMRuntime(config, generation=generation)


def get_llm_runtime() -> LLMRuntime:
    """Return the process runtime, constructing it lazily on first access."""
    with _managed_runtime_lock:
        if _managed_state.shutting_down:
            raise _RuntimeClosingError
        if _managed_state.runtime is None:
            _managed_state.runtime = _build_managed_runtime(
                generation=_managed_state.generation
            )
        return _managed_state.runtime


async def initialize_llm_runtime() -> LLMRuntime:
    """Initialize once, serialized with reload and shutdown operations."""
    ticket = await _lifecycle_coordinator.acquire()
    try:
        return get_llm_runtime()
    finally:
        _lifecycle_coordinator.release(ticket)


async def reload_llm_runtime() -> LLMRuntime:
    """Publish a valid candidate, then close the old runtime.

    A close failure is propagated after the swap; the new generation remains
    published because rolling back to a partially closed runtime is unsafe.
    Reloads are serialized through retirement of the prior generation. Each
    call therefore returns its candidate before a later lifecycle operation is
    allowed to retire it.
    """
    ticket = await _lifecycle_coordinator.acquire()
    try:
        with _managed_runtime_lock:
            next_generation = _managed_state.generation + 1
            candidate = _build_managed_runtime(generation=next_generation)
            previous = _managed_state.runtime
            _managed_state.runtime = candidate
            _managed_state.generation = next_generation
            invalidate_capability_cache()
        if previous is not None and previous is not candidate:
            await _finish_cleanup_before_cancellation(previous.close())
        return candidate
    finally:
        _lifecycle_coordinator.release(ticket)


async def shutdown_llm_runtime() -> None:
    """Detach and close the process runtime, if it was initialized."""
    ticket = await _lifecycle_coordinator.acquire()
    try:
        with _managed_runtime_lock:
            _managed_state.shutting_down = True
            managed = _managed_state.runtime
            _managed_state.runtime = None
        try:
            if managed is not None:
                await _finish_cleanup_before_cancellation(managed.close())
        finally:
            with _managed_runtime_lock:
                _managed_state.shutting_down = False
    finally:
        _lifecycle_coordinator.release(ticket)


__all__ = [
    "LLMRuntime",
    "RuntimeState",
    "get_llm_runtime",
    "initialize_llm_runtime",
    "reload_llm_runtime",
    "shutdown_llm_runtime",
]
