"""Managed lifecycle and stable response facade for LLM providers."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import inspect
import sys
import threading
import time
from typing import TYPE_CHECKING, Any, Literal, cast

from .backends import LiteLLMBackend, OpenAIBackend
from .capabilities import invalidate_capability_cache
from .config import LLMRuntimeConfig, load_llm_runtime_config, resolve_profile
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
from .events import project_stream_event
from .observability import LLMCallRecord, StructuredLLMObserver
from .security import (
    CONTROL_PLANE_KEYS,
    contains_control_plane_key,
    sanitize_message,
    thaw_value,
)
from .types import LLMEvent, LLMProfile, LLMResponse, LLMUsage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable

    from ...core.runtime_config import RuntimeConfig

type RuntimeState = Literal["NEW", "RUNNING", "CLOSING", "CLOSED"]

HTTP_RATE_LIMITED = 429
MAX_OBSERVABILITY_COUNT = 2**31 - 1


@dataclass(frozen=True, slots=True)
class _Observation:
    request_id: str | None = None
    usage: LLMUsage | None = None
    sdk_metadata: object | None = None


@dataclass(slots=True)
class _StreamAssembly:
    profile: LLMProfile
    text_parts: list[str]
    output_items: list[object]
    usage: LLMUsage | None = None
    last_raw: object | None = None
    request_id: str | None = None
    model: str | None = None
    terminal: bool = False
    failed: bool = False

    def accept(self, projected: LLMEvent) -> LLMEvent:
        """Update assembled state and finalize provider completion events."""
        request_id = _stream_string(projected.raw, "_request_id", "request_id", "id")
        model = _stream_string(projected.raw, "model")
        if request_id:
            self.request_id = request_id
        if model:
            self.model = model
        if projected.type == "text_delta" and type(projected.data) is str:
            self.text_parts.append(projected.data)
        elif projected.type == "output_item":
            self.output_items.append(projected.data)
        elif projected.type == "usage" and isinstance(projected.data, LLMUsage):
            self.usage = projected.data
        elif projected.type == "completed":
            self.terminal = True
            return LLMEvent(
                type="completed",
                data=self._provider_response(projected.data),
                raw=projected.raw,
            )
        elif projected.type == "error":
            self.terminal = True
            self.failed = True
        return projected

    def _provider_response(self, raw_response: object) -> LLMResponse:
        chat = self.profile.litellm_generation == "chat"
        response = _normalize_response(
            raw_response,
            profile=self.profile,
            chat=chat,
        )
        assembled_text = "".join(self.text_parts) if self.text_parts else None
        text_present, terminal_text = _terminal_text(raw_response, chat=chat)
        output_present, terminal_output = _terminal_output(raw_response)
        request_present, terminal_request_id = _terminal_string(
            raw_response, "_request_id", "request_id", "id"
        )
        model_present, terminal_model = _terminal_string(raw_response, "model")
        return LLMResponse(
            text=terminal_text if text_present else assembled_text,
            output=terminal_output if output_present else tuple(self.output_items),
            usage=response.usage if response.usage is not None else self.usage,
            request_id=(terminal_request_id if request_present else self.request_id),
            model=(
                terminal_model if model_present else self.model or self.profile.model
            ),
            backend=response.backend,
            raw=response.raw,
        )

    def completion(self) -> LLMEvent:
        return LLMEvent(
            type="completed",
            data=LLMResponse(
                text="".join(self.text_parts) if self.text_parts else None,
                output=tuple(self.output_items),
                usage=self.usage,
                request_id=self.request_id,
                model=self.model or self.profile.model,
                backend=self.profile.backend,
                raw=self.last_raw,
            ),
            raw=self.last_raw,
        )


class _RuntimeClosingError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("LLM runtime is closing or closed")


class _ForeignLoopError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("LLM runtime is bound to another active event loop")


class _InvalidProfileError(LLMConfigurationError):
    def __init__(self) -> None:
        super().__init__("invalid LLM profile")


class _WrongBackendError(LLMConfigurationError):
    def __init__(self, actual: str, expected: str) -> None:
        super().__init__(f"profile backend is {actual}, not {expected}")


class _ControlPlaneParameterError(LLMConfigurationError):
    def __init__(self) -> None:
        super().__init__(
            "control-plane parameters are not accepted by stable LLM calls"
        )


class _InvalidStreamContextError(TypeError):
    def __init__(self) -> None:
        super().__init__("stream context entry must be awaitable")


def _fingerprint(secret: str | None) -> str:
    # SHA-256 produces a stable cache key for LLM profile lookup by API key;
    # this is NOT password storage. argon2/bcrypt are unsuitable because their
    # random salts make them non-deterministic and unusable as dict keys.
    # CodeQL py/weak-sensitive-data-hashing flagged this as false positive
    # (dismissed: alert #2).
    value = secret.encode("utf-8", errors="replace") if secret else b""
    return hashlib.sha256(value).hexdigest()


def _stream_string(source: object | None, *names: str) -> str | None:
    if source is None:
        return None
    value = _value(source, *names)
    return sanitize_message(value) if type(value) is str else None


_MISSING = object()


def _member(source: object, name: str) -> tuple[bool, object | None]:
    """Read one provider member while containing hostile SDK objects."""
    try:
        if isinstance(source, Mapping):
            mapping = cast("Mapping[object, object]", source)
            if name in mapping:
                return True, mapping[name]
            return False, None
    except asyncio.CancelledError:
        raise
    except BaseException:
        return False, None
    try:
        value = getattr(source, name, _MISSING)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return False, None
    return (False, None) if value is _MISSING else (True, value)


def _value(source: object, *names: str) -> object | None:
    for name in names:
        present, value = _member(source, name)
        if present and value is not None:
            return value
    return None


def _safe_int(value: object | None) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _safe_float(value: object | None) -> float | None:
    if type(value) is int:
        return float(value) if value >= 0 else None
    if type(value) is float:
        return value if value >= 0 else None
    return None


def _metadata_member(source: object, name: str) -> object | None:
    """Read one SDK metadata member without trusting provider-owned objects."""
    try:
        if isinstance(source, Mapping):
            mapping = cast("Mapping[object, object]", source)
            return mapping.get(name)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return None
    try:
        return getattr(source, name)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return None


def _bounded_metadata_count(
    source: object,
    paths: tuple[tuple[str, ...], ...],
) -> int | None:
    for path in paths:
        value: object | None = source
        for name in path:
            if value is None:
                break
            value = _metadata_member(value, name)
        if type(value) is int and 0 <= value <= MAX_OBSERVABILITY_COUNT:
            return value
    return None


def _attempt_counts(source: object) -> tuple[int | None, int | None]:
    retry_count = _bounded_metadata_count(
        source,
        (
            (
                "_hidden_params",
                "additional_headers",
                "x-litellm-attempted-retries",
            ),
            ("metadata", "attempted_retries"),
            ("_metadata", "attempted_retries"),
            ("litellm_params", "metadata", "attempted_retries"),
            ("attempted_retries",),
            ("retry_count",),
        ),
    )
    fallback_count = _bounded_metadata_count(
        source,
        (
            (
                "_hidden_params",
                "additional_headers",
                "x-litellm-attempted-fallbacks",
            ),
            ("metadata", "attempted_fallbacks"),
            ("metadata", "fallback_depth"),
            ("_metadata", "attempted_fallbacks"),
            ("_metadata", "fallback_depth"),
            ("litellm_params", "metadata", "attempted_fallbacks"),
            ("litellm_params", "metadata", "fallback_depth"),
            ("attempted_fallbacks",),
            ("fallback_count",),
            ("fallback_depth",),
        ),
    )
    return retry_count, fallback_count


def _usage(raw: object) -> LLMUsage | None:
    source = _value(raw, "usage")
    if source is None:
        return None
    input_tokens = _safe_int(_value(source, "input_tokens", "prompt_tokens"))
    output_tokens = _safe_int(_value(source, "output_tokens", "completion_tokens"))
    total_tokens = _safe_int(_value(source, "total_tokens"))
    cost = _safe_float(_value(source, "cost", "response_cost"))
    input_details = _value(source, "input_tokens_details", "prompt_tokens_details")
    output_details = _value(
        source, "output_tokens_details", "completion_tokens_details"
    )
    cached_tokens = _safe_int(_value(input_details, "cached_tokens"))
    reasoning_tokens = _safe_int(_value(output_details, "reasoning_tokens"))
    if all(
        value is None
        for value in (
            input_tokens,
            output_tokens,
            total_tokens,
            cost,
            cached_tokens,
            reasoning_tokens,
        )
    ):
        return None
    return LLMUsage(
        input_tokens,
        output_tokens,
        total_tokens,
        cost,
        cached_tokens,
        reasoning_tokens,
    )


def _response_text(raw: object, *, chat: bool) -> str | None:
    if not chat:
        value = _value(raw, "output_text")
        return value if type(value) is str else None
    choices = _value(raw, "choices")
    if not isinstance(choices, (list, tuple)) or not choices:
        return None
    try:
        first_choice = choices[0]
    except asyncio.CancelledError:
        raise
    except BaseException:
        return None
    message = _value(first_choice, "message")
    content = _value(message, "content") if message is not None else None
    return content if type(content) is str else None


def _normalize_response(raw: object, *, profile: LLMProfile, chat: bool) -> LLMResponse:
    output_value = _value(raw, "output")
    try:
        output = tuple(output_value) if isinstance(output_value, (list, tuple)) else ()
    except asyncio.CancelledError:
        raise
    except BaseException:
        output = ()
    request_id_value = _value(raw, "_request_id", "request_id", "id")
    request_id = (
        sanitize_message(request_id_value) if type(request_id_value) is str else None
    )
    model = _value(raw, "model")
    return LLMResponse(
        text=_response_text(raw, chat=chat),
        output=output,
        usage=_usage(raw),
        request_id=request_id,
        model=model if type(model) is str else profile.model,
        backend=profile.backend,
        raw=raw,
    )


def _terminal_text(raw: object, *, chat: bool) -> tuple[bool, str | None]:
    if not chat:
        present, value = _member(raw, "output_text")
        return present, value if type(value) is str else None
    choices_present, choices = _member(raw, "choices")
    if not choices_present:
        return False, None
    if not isinstance(choices, (list, tuple)) or not choices:
        return True, None
    try:
        first_choice = choices[0]
    except asyncio.CancelledError:
        raise
    except BaseException:
        return True, None
    message_present, message = _member(first_choice, "message")
    if not message_present or message is None:
        return message_present, None
    content_present, content = _member(message, "content")
    return content_present, content if type(content) is str else None


def _terminal_output(raw: object) -> tuple[bool, tuple[object, ...]]:
    present, value = _member(raw, "output")
    if not present:
        return False, ()
    if not isinstance(value, (list, tuple)):
        return True, ()
    try:
        return True, tuple(value)
    except asyncio.CancelledError:
        raise
    except BaseException:
        return True, ()


def _terminal_string(raw: object, *names: str) -> tuple[bool, str | None]:
    for name in names:
        present, value = _member(raw, name)
        if present:
            return True, sanitize_message(value) if type(value) is str else None
    return False, None


def _normalized_error(exc: Exception, profile: LLMProfile) -> LLMError:
    status = _safe_int(_value(exc, "status_code"))
    request_id = _value(exc, "request_id", "_request_id")
    metadata: dict[str, object] = {
        "backend": profile.backend,
        "model": profile.model,
        "request_id": request_id if type(request_id) is str else None,
        "status_code": status,
    }
    name = type(exc).__name__.casefold()
    if isinstance(exc, ModuleNotFoundError):
        error_type = LLMDependencyError
    elif status in {401, 403} or "authentication" in name:
        error_type = LLMAuthenticationError
    elif status == HTTP_RATE_LIMITED or "ratelimit" in name or "rate_limit" in name:
        error_type = LLMRateLimitError
        metadata["retryable"] = True
    elif status in {408, 504} or "timeout" in name:
        error_type = LLMTimeoutError
        metadata["retryable"] = True
    elif "connection" in name:
        error_type = LLMConnectionError
        metadata["retryable"] = True
    else:
        error_type = LLMProviderError
    return error_type("LLM provider call failed", **cast("Any", metadata))


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


class LLMRuntime:
    """Own resolved profiles, provider backends, and their shutdown lifecycle."""

    def __init__(
        self,
        config: LLMRuntimeConfig,
        *,
        legacy: RuntimeConfig,
        generation: int = 0,
        observer: StructuredLLMObserver | None = None,
    ) -> None:
        self.config = config
        self._legacy = legacy
        self.generation = generation
        self._observer = observer or StructuredLLMObserver(
            enabled=bool(config.observability.values.get("enabled", True))
        )
        self._profiles: dict[tuple[str, int, str], LLMProfile] = {}
        self._backends: dict[
            tuple[str, int, str, str], OpenAIBackend | LiteLLMBackend
        ] = {}
        self._owned_backends: list[Any] = []
        self._pending_retirements: list[Any] = []
        self._retired_backends: list[Any] = []
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
        """Resolve and cache one named administrator-controlled profile."""
        with self._lock:
            self._ensure_running()
            selected = name or self.config.default_profile
            try:
                resolved = resolve_profile(
                    self.config, legacy=self._legacy, name=selected
                )
            except (KeyError, ValueError) as exc:
                raise _InvalidProfileError from exc
            key = (selected, self.generation, _fingerprint(resolved.api_key))
            cached = self._profiles.get(key)
            if cached is None:
                stale = [
                    existing
                    for existing in self._profiles
                    if existing[:2] == (selected, self.generation)
                ]
                for existing in stale:
                    self._profiles.pop(existing, None)
                self._profiles[key] = resolved
                cached = resolved
            return cached

    def _backend(
        self, backend: Literal["litellm", "openai"], name: str | None
    ) -> OpenAIBackend | LiteLLMBackend:
        with self._lock:
            profile = self.profile(name)
            if profile.backend != backend:
                raise _WrongBackendError(profile.backend, backend)
            key = (
                profile.name,
                self.generation,
                _fingerprint(profile.api_key),
                backend,
            )
            cached = self._backends.get(key)
            if cached is None:
                stale_keys = [
                    existing
                    for existing in self._backends
                    if existing[0] == profile.name
                    and existing[1] == self.generation
                    and existing[3] == backend
                ]
                for stale_key in stale_keys:
                    stale_backend = self._backends.pop(stale_key)
                    self._owned_backends = [
                        owned
                        for owned in self._owned_backends
                        if owned is not stale_backend
                    ]
                    self._retired_backends.append(stale_backend)
                    self._pending_retirements.append(stale_backend)
                cached = (
                    OpenAIBackend(profile)
                    if backend == "openai"
                    else LiteLLMBackend(profile, self.config.router)
                )
                self._backends[key] = cached
                self._owned_backends.append(cached)
            return cached

    def openai(self, name: str | None = None) -> OpenAIBackend:
        """Return the runtime-owned native OpenAI backend."""
        return cast("OpenAIBackend", self._backend("openai", name))

    def litellm(self, name: str | None = None) -> LiteLLMBackend:
        """Return the runtime-owned native LiteLLM backend."""
        return cast("LiteLLMBackend", self._backend("litellm", name))

    async def respond(
        self,
        input: object,
        *,
        profile: str | None = None,
        **params: object,
    ) -> LLMResponse:
        """Generate one normalized response through the configured operation."""
        self._bind_async_loop()
        rejected = CONTROL_PLANE_KEYS.intersection(params)
        if rejected:
            raise _ControlPlaneParameterError
        selected = self.profile(profile)
        if contains_control_plane_key(selected.provider_options):
            raise _ControlPlaneParameterError
        started = time.perf_counter()
        try:
            defaults = thaw_value(selected.provider_options)
            merged = cast("dict[str, Any]", defaults)
            merged.update(params)
            if selected.backend == "openai":
                merged["model"] = selected.model
                merged["input"] = input
                backend = self.openai(selected.name)
                await self._drain_retirements()
                raw = await backend.client.responses.create(**merged)
                response = _normalize_response(raw, profile=selected, chat=False)
            else:
                operation = (
                    "aresponses"
                    if selected.litellm_generation == "responses"
                    else "acompletion"
                )
                input_key = "input" if operation == "aresponses" else "messages"
                merged["model"] = selected.model
                merged[input_key] = input
                backend = self.litellm(selected.name)
                await self._drain_retirements()
                raw = await backend.call(operation, **merged)
                response = _normalize_response(
                    raw, profile=selected, chat=operation == "acompletion"
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error = _normalized_error(exc, selected)
            self._emit(
                selected,
                started,
                _error_status(error),
                observation=_Observation(
                    request_id=error.request_id,
                    sdk_metadata=exc,
                ),
            )
            raise error from exc
        self._emit(
            selected,
            started,
            "success",
            observation=_Observation(
                request_id=response.request_id,
                usage=response.usage,
                sdk_metadata=response.raw,
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
        """Yield a stable, lossless projection of one provider-native stream."""
        self._bind_async_loop()
        rejected = CONTROL_PLANE_KEYS.intersection(params)
        if rejected:
            raise _ControlPlaneParameterError
        selected = self.profile(profile)
        if contains_control_plane_key(selected.provider_options):
            raise _ControlPlaneParameterError
        started = time.perf_counter()
        native_stream: object | None = None
        entered_stream: object | None = None
        iterator: object | None = None
        entered = False
        assembly = _StreamAssembly(selected, [], [])
        try:
            native_stream = await self._create_native_stream(selected, input, params)
            entered_stream, entered = await self._enter_stream(native_stream)
            iterator = self._stream_iterator(entered_stream)
            yield LLMEvent(type="started", data=selected, raw=None)
            while True:
                try:
                    raw = await anext(cast("AsyncIterator[object]", iterator))
                except StopAsyncIteration:
                    break
                assembly.last_raw = raw
                for projected in project_stream_event(raw):
                    yield assembly.accept(projected)
            if not assembly.terminal:
                yield assembly.completion()
            self._emit(
                selected,
                started,
                "provider_error" if assembly.failed else "success",
                operation="stream",
                observation=_Observation(
                    request_id=assembly.request_id,
                    usage=assembly.usage,
                    sdk_metadata=assembly.last_raw,
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
                observation=_Observation(
                    request_id=error.request_id,
                    sdk_metadata=exc,
                ),
            )
            raise error from exc
        finally:
            if native_stream is not None:
                await self._close_stream_resources(
                    native_stream,
                    entered_stream=entered_stream,
                    iterator=iterator,
                    entered=entered,
                )

    async def _create_native_stream(
        self,
        profile: LLMProfile,
        input: object,
        params: Mapping[str, object],
    ) -> object:
        merged = cast("dict[str, Any]", thaw_value(profile.provider_options))
        merged.update(params)
        merged["stream"] = True
        if profile.backend == "openai":
            merged["model"] = profile.model
            merged["input"] = input
            backend = self.openai(profile.name)
            await self._drain_retirements()
            return await backend.client.responses.create(**merged)
        operation = (
            "aresponses" if profile.litellm_generation == "responses" else "acompletion"
        )
        merged["input" if operation == "aresponses" else "messages"] = input
        backend = self.litellm(profile.name)
        await self._drain_retirements()
        return await backend.call(operation, **merged)

    @staticmethod
    async def _enter_stream(stream: object) -> tuple[object, bool]:
        enter = getattr(stream, "__aenter__", None)
        if not callable(enter):
            return stream, False
        result = enter()
        if not inspect.isawaitable(result):
            raise _InvalidStreamContextError
        return await cast("Awaitable[object]", result), True

    @staticmethod
    def _stream_iterator(stream: object) -> object:
        return cast("Any", stream).__aiter__()

    @classmethod
    async def _close_stream_resources(
        cls,
        native_stream: object,
        *,
        entered_stream: object | None,
        iterator: object | None,
        entered: bool,
    ) -> None:
        """Close each distinct stream layer, including a context manager."""
        active_exception = sys.exc_info()[0] is not None
        first_error: BaseException | None = None
        resources: list[tuple[object, bool]] = []
        if iterator is not None:
            resources.append((iterator, False))
        if entered_stream is not None and all(
            entered_stream is not resource for resource, _ in resources
        ):
            resources.append((entered_stream, False))
        if all(native_stream is not resource for resource, _ in resources):
            resources.append((native_stream, entered))
        elif entered:
            resources = [
                (resource, True if resource is native_stream else as_context)
                for resource, as_context in resources
            ]
        for resource, as_context in resources:
            try:
                await cls._close_stream(resource, entered=as_context)
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None and not active_exception:
            raise first_error

    @staticmethod
    async def _close_stream(stream: object, *, entered: bool) -> None:
        """Close one stream without replacing an active provider/cancellation error."""
        exception_info = sys.exc_info()
        active_exception = exception_info[0] is not None
        current = exception_info[1]
        if isinstance(current, LLMError) and isinstance(current.__cause__, Exception):
            cause = current.__cause__
            exception_info = (type(cause), cause, cause.__traceback__)
        try:
            if entered:
                exit_context = getattr(stream, "__aexit__", None)
                if callable(exit_context):
                    result = exit_context(*exception_info)
                    if inspect.isawaitable(result):
                        await cast("Awaitable[object]", result)
                    return
            close = getattr(stream, "aclose", None)
            if not callable(close):
                close = getattr(stream, "close", None)
            if callable(close):
                result = close()
                if inspect.isawaitable(result):
                    await cast("Awaitable[object]", result)
        except BaseException:
            if not active_exception:
                raise

    async def _drain_retirements(self) -> None:
        self._bind_async_loop()
        with self._lock:
            pending = tuple(self._pending_retirements)
            self._pending_retirements.clear()
        for index, backend in enumerate(pending):
            try:
                await self._close_backend(backend)
            except asyncio.CancelledError:
                with self._lock:
                    self._pending_retirements[:0] = pending[index:]
                raise

    async def _close_backend(self, backend: object) -> None:
        try:
            result = cast("Any", backend).close()
            if inspect.isawaitable(result):
                await cast("Awaitable[object]", result)
        except asyncio.CancelledError:
            raise
        except Exception:
            return
        with self._lock:
            self._retired_backends = [
                retired for retired in self._retired_backends if retired is not backend
            ]

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
        retry_count, fallback_count = (
            _attempt_counts(details.sdk_metadata)
            if details.sdk_metadata is not None
            else (None, None)
        )
        try:
            self._observer.emit(
                LLMCallRecord(
                    operation=operation,
                    profile=profile.name,
                    backend=profile.backend,
                    model=profile.model,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    status=status,
                    request_id=details.request_id,
                    usage=details.usage,
                    retry_count=retry_count,
                    fallback_count=fallback_count,
                )
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return

    def _release_backend(self, backend: object) -> None:
        with self._lock:
            self._owned_backends = [
                owned for owned in self._owned_backends if owned is not backend
            ]
            self._retired_backends = [
                retired for retired in self._retired_backends if retired is not backend
            ]
            self._pending_retirements = [
                pending
                for pending in self._pending_retirements
                if pending is not backend
            ]

    async def _close_owned(self) -> None:
        with self._lock:
            candidates = (*self._retired_backends, *self._owned_backends)
            self._backends.clear()
            self._profiles.clear()
        unique = tuple(dict.fromkeys(map(id, candidates)))
        by_id = {id(backend): backend for backend in candidates}
        for backend_id in unique:
            backend = by_id[backend_id]
            try:
                result = backend.close()
                if inspect.isawaitable(result):
                    await cast("Awaitable[object]", result)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            self._release_backend(backend)
        with self._lock:
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

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._busy = False

    def _claim(self, ticket: _LifecycleTicket) -> bool:
        with self._condition:
            while self._busy and ticket.active:
                self._condition.wait()
            if not ticket.active:
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
            claimed = await asyncio.to_thread(self._claim, ticket)
        except BaseException:
            self._cancel(ticket)
            raise
        if not claimed:
            raise asyncio.CancelledError
        return ticket

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


async def _finish_cleanup_before_cancellation(cleanup: Awaitable[None]) -> None:
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
    from ...core.runtime_config import runtime_config

    config = load_llm_runtime_config(legacy=runtime_config)
    return LLMRuntime(config, legacy=runtime_config, generation=generation)


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
