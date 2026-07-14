"""Stable project-owned LLM exception hierarchy."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from .security import redact_value, sanitize_message

if TYPE_CHECKING:
    from typing import Unpack

    from .types import LLMBackendName


class LLMErrorMetadata(TypedDict, total=False):
    """Safe metadata attached to normalized provider failures."""

    backend: LLMBackendName | None
    model: str | None
    request_id: str | None
    status_code: int | None
    retryable: bool


class LLMError(RuntimeError):
    """Base error for failures normalized by the stable LLM facade."""

    default_message = ""

    def __init__(
        self,
        *args: object,
        **metadata: Unpack[LLMErrorMetadata],
    ) -> None:
        effective_args = args or (
            (self.default_message,) if self.default_message else ()
        )
        safe_args = tuple(
            sanitize_message(argument)
            if type(argument) is str
            else redact_value(argument)
            for argument in effective_args
        )
        super().__init__(*safe_args)
        backend = metadata.get("backend")
        self.backend = (
            backend
            if type(backend) is str and backend in {"litellm", "openai"}
            else None
        )
        model = metadata.get("model")
        self.model = sanitize_message(model) if type(model) is str else None
        request_id = metadata.get("request_id")
        self.request_id = (
            sanitize_message(request_id) if type(request_id) is str else None
        )
        status_code = metadata.get("status_code")
        self.status_code = status_code if type(status_code) is int else None
        retryable = metadata.get("retryable", False)
        self.retryable = retryable if type(retryable) is bool else False


class LLMDependencyError(LLMError):
    """A configured provider dependency is unavailable."""


class LLMConfigurationError(LLMError):
    """LLM configuration is invalid or unsafe."""


class LLMAuthenticationError(LLMError):
    """A provider rejected configured credentials."""


class LLMRateLimitError(LLMError):
    """A provider rate limit prevented the operation."""


class LLMTimeoutError(LLMError):
    """A provider operation exceeded its deadline."""


class LLMConnectionError(LLMError):
    """A provider connection could not be established or maintained."""


class LLMResponseError(LLMError):
    """A provider response could not be projected safely."""


class MissingLLMContentError(LLMResponseError):
    """LLM response did not contain message content."""

    default_message = "LLM response did not contain message content"


class EmptyLLMContentError(LLMResponseError):
    """LLM response content was empty."""

    default_message = "LLM response content was empty"


class LLMProviderError(LLMError):
    """LLM provider call failed."""

    default_message = "LLM provider call failed"


__all__ = [
    "EmptyLLMContentError",
    "LLMAuthenticationError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMDependencyError",
    "LLMError",
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
    "MissingLLMContentError",
]
