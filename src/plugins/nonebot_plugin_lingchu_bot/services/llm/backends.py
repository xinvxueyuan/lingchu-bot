"""Managed provider SDK backends."""

from __future__ import annotations

import inspect
import threading
from typing import TYPE_CHECKING, Any, cast

from .security import thaw_value

if TYPE_CHECKING:
    from types import ModuleType

    from openai import AsyncOpenAI

    from .config import LiteLLMRouterConfig
    from .types import LLMProfile

_ROUTER_CONTROL_KEYS = frozenset({
    "callbacks",
    "custom_logger",
    "failure_callback",
    "logger_fn",
    "loggers",
    "success_callback",
})
_NO_CREDENTIAL_API_KEY = "__lingchu_no_credential__"


class _OpenAIBackendClosedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("OpenAIBackend is closed")


class _LiteLLMBackendClosedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("LiteLLMBackend is closed")


class _MissingBackendDependencyError(ModuleNotFoundError):
    def __init__(self, backend: str, dependency: str) -> None:
        super().__init__(
            f"{backend} backend requires the optional '{dependency}' dependency"
        )


class _InvalidLiteLLMOperationError(ValueError):
    def __init__(self) -> None:
        super().__init__("invalid LiteLLM operation")


class _AsyncLiteLLMOperationError(TypeError):
    def __init__(self) -> None:
        super().__init__("LiteLLM operation must be asynchronous")


class _RouterControlOptionsError(ValueError):
    def __init__(self) -> None:
        super().__init__("LiteLLM Router callbacks and loggers are not supported")


class _RouterOptionCollisionError(ValueError):
    def __init__(self) -> None:
        super().__init__("LiteLLM Router extension collides with managed option")


class _RouterUnavailableError(TypeError):
    def __init__(self) -> None:
        super().__init__("LiteLLM Router is unavailable")


def _contains_router_control_key(value: object) -> bool:
    if type(value) is dict:
        mapping = cast("dict[str, object]", value)
        return any(
            key.casefold() in _ROUTER_CONTROL_KEYS
            or _contains_router_control_key(child)
            for key, child in mapping.items()
        )
    if type(value) is list:
        sequence = cast("list[object]", value)
        return any(_contains_router_control_key(child) for child in sequence)
    return False


def _inject_router_no_credential_defaults(values: dict[str, Any]) -> None:
    model_list = values.get("model_list")
    if not isinstance(model_list, list):
        return
    for deployment in model_list:
        if not isinstance(deployment, dict):
            continue
        litellm_params = deployment.get("litellm_params")
        if isinstance(litellm_params, dict) and not litellm_params.get("api_key"):
            litellm_params["api_key"] = _NO_CREDENTIAL_API_KEY


class OpenAIBackend:
    """Lazily construct and own one OpenAI async client for a profile."""

    def __init__(self, profile: LLMProfile) -> None:
        self.profile = profile
        self._client: Any = None
        self._client_profile: LLMProfile | None = None
        self._owned_clients: list[Any] = []
        self._closed = False
        self._lock = threading.RLock()

    @property
    def client(self) -> AsyncOpenAI:
        """Return the lazily-created native SDK client."""
        with self._lock:
            if self._closed:
                raise _OpenAIBackendClosedError
            if self._client is None or self._client_profile != self.profile:
                try:
                    from openai import AsyncOpenAI
                except ModuleNotFoundError as exc:
                    if exc.name == "openai":
                        raise _MissingBackendDependencyError(
                            "OpenAI", "openai"
                        ) from exc
                    raise
                self._client = AsyncOpenAI(
                    api_key=self.profile.api_key or _NO_CREDENTIAL_API_KEY,
                    base_url=self.profile.base_url,
                    organization=self.profile.organization,
                    project=self.profile.project,
                    timeout=self.profile.timeout,
                    max_retries=self.profile.max_retries,
                    default_headers=dict(self.profile.default_headers),
                    default_query=dict(self.profile.default_query),
                )
                self._client_profile = self.profile
                self._owned_clients.append(self._client)
            return cast("AsyncOpenAI", self._client)

    def with_options(self, **options: object) -> AsyncOpenAI:
        """Return the SDK's native option copy without creating a new owned client."""
        return self.client.with_options(**cast("dict[str, Any]", options))

    async def close(self) -> None:
        """Close the owned client once; repeated calls are harmless."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            clients = tuple(self._owned_clients)
            self._client = None
            self._owned_clients.clear()
        for client in clients:
            try:
                result = client.close()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                continue


class LiteLLMBackend:
    """Lazy, deliberately small native access wrapper around LiteLLM."""

    def __init__(
        self,
        profile: LLMProfile,
        router: LiteLLMRouterConfig | None = None,
        *,
        _forward_max_retries: bool = True,
    ) -> None:
        self.profile = profile
        self._sdk: ModuleType | None = None
        self._router_config = router
        self._router: object | None = None
        self._forward_max_retries = _forward_max_retries
        self._closed = False
        self._lock = threading.RLock()

    @property
    def sdk(self) -> ModuleType:
        """Return the lazily imported LiteLLM module unchanged."""
        with self._lock:
            if self._closed:
                raise _LiteLLMBackendClosedError
            if self._sdk is None:
                try:
                    import litellm
                except ModuleNotFoundError as exc:
                    if exc.name == "litellm":
                        raise _MissingBackendDependencyError(
                            "LiteLLM", "litellm"
                        ) from exc
                    raise
                self._sdk = litellm
            return self._sdk

    @property
    def router(self) -> object | None:
        """Build an isolated Router only when explicitly enabled."""
        with self._lock:
            if self._closed:
                raise _LiteLLMBackendClosedError
            if self._router is not None:
                return self._router
            config = self._router_config
            if config is None:
                return None
            thawed_values = thaw_value(config.values)
            values = cast("dict[str, Any]", thawed_values)
            enabled = bool(values.pop("enabled", False))
            if not enabled:
                return None
            if _contains_router_control_key(values):
                raise _RouterControlOptionsError
            extensions = cast("dict[str, Any]", values.pop("extensions", {}))
            strategy = values.pop("strategy", None)
            collision_keys = set(values)
            collision_keys.add("routing_strategy")
            if collision_keys.intersection(extensions):
                raise _RouterOptionCollisionError
            values.update(extensions)
            if strategy is not None:
                values["routing_strategy"] = strategy
            _inject_router_no_credential_defaults(values)
            router_cls = getattr(self.sdk, "Router", None)
            if not callable(router_cls):
                raise _RouterUnavailableError
            self._router = router_cls(**values)
            return self._router

    async def call(self, operation: str, /, **params: Any) -> Any:
        """Invoke one public asynchronous LiteLLM operation without adaptation."""
        if (
            not operation
            or not operation.isidentifier()
            or operation.startswith("_")
            or "." in operation
            or "/" in operation
            or "\\" in operation
        ):
            raise _InvalidLiteLLMOperationError
        target = getattr(self.sdk, operation, None)
        if not inspect.iscoroutinefunction(target):
            raise _AsyncLiteLLMOperationError
        thawed_options = thaw_value(self.profile.provider_options)
        provider_options = cast("dict[str, Any]", thawed_options)
        merged: dict[str, Any] = {
            "model": self.profile.model,
            "timeout": self.profile.timeout,
            "api_key": self.profile.api_key or _NO_CREDENTIAL_API_KEY,
        }
        if self._forward_max_retries:
            merged["max_retries"] = self.profile.max_retries
        if self.profile.base_url is not None:
            merged["api_base"] = self.profile.base_url
        if self.profile.default_headers:
            merged["extra_headers"] = dict(self.profile.default_headers)
        if self.profile.default_query:
            merged["extra_query"] = dict(self.profile.default_query)
        if self.profile.organization is not None:
            merged["organization"] = self.profile.organization
        if self.profile.project is not None:
            merged["project"] = self.profile.project
        merged.update(provider_options)
        merged.update(params)
        return await target(**merged)

    async def close(self) -> None:
        """Release runtime-owned references; never mutate LiteLLM globals."""
        self.release()

    def release(self) -> None:
        """Synchronously release references held by a probe-only backend."""
        with self._lock:
            self._closed = True
            self._router = None
            self._sdk = None


__all__ = ["LiteLLMBackend", "OpenAIBackend"]
