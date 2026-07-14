from __future__ import annotations

from typing import Any, cast, override

from src.plugins.nonebot_plugin_lingchu_bot.services import llm
from src.plugins.nonebot_plugin_lingchu_bot.services.llm import compat
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.errors import (
    EmptyLLMContentError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMDependencyError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    MissingLLMContentError,
)


def _raise_on_args(_error: BaseException) -> tuple[object, ...]:
    raise AssertionError


HostileArgsError = cast(
    "type[RuntimeError]",
    type("HostileArgsError", (RuntimeError,), {"args": property(_raise_on_args)}),
)


class HostileReprError(AssertionError):
    """Raised if an unsafe repr is invoked."""


class HostileRepr:
    @override
    def __repr__(self) -> str:
        raise HostileReprError


def test_error_metadata_is_available_without_entering_public_message() -> None:
    error = LLMRateLimitError(
        "Provider rate limit exceeded",
        backend="openai",
        model="gpt-test",
        request_id="req-123",
        status_code=429,
        retryable=True,
    )

    assert str(error) == "Provider rate limit exceeded"
    assert error.backend == "openai"
    assert error.model == "gpt-test"
    assert error.request_id == "req-123"
    assert error.status_code == 429
    assert error.retryable is True


def test_error_metadata_is_sanitized_and_typed() -> None:
    error = LLMError(
        "safe",
        backend=cast("Any", HostileRepr()),
        model="model\n token=secret-token",
        request_id="req\n token=secret-token",
        status_code=cast("Any", "429"),
        retryable=cast("Any", "yes"),
    )
    assert error.backend is None
    assert error.model == "model  token=<redacted>"
    assert error.request_id == "req  token=<redacted>"
    assert error.status_code is None
    assert error.retryable is False


def test_error_metadata_never_calls_hostile_repr() -> None:
    error = LLMError(
        "safe",
        model=cast("Any", HostileRepr()),
        request_id=cast("Any", HostileRepr()),
    )
    assert error.model is None
    assert error.request_id is None


def test_error_hierarchy_contains_all_stable_categories() -> None:
    categories = (
        LLMDependencyError,
        LLMConfigurationError,
        LLMAuthenticationError,
        LLMRateLimitError,
        LLMTimeoutError,
        LLMConnectionError,
        LLMResponseError,
        LLMProviderError,
    )

    assert all(issubclass(category, LLMError) for category in categories)


def test_legacy_errors_keep_identity_and_default_messages() -> None:
    assert llm.LLMError is compat.LLMError is LLMError
    assert llm.MissingLLMContentError is compat.MissingLLMContentError
    assert llm.EmptyLLMContentError is compat.EmptyLLMContentError
    assert llm.LLMProviderError is compat.LLMProviderError
    assert str(MissingLLMContentError()) == (
        "LLM response did not contain message content"
    )
    assert str(EmptyLLMContentError()) == "LLM response content was empty"
    assert str(LLMProviderError()) == "LLM provider call failed"


def test_error_message_strips_log_injection_controls() -> None:
    error = LLMError("safe\r\nforged\x00entry")

    assert "\r" not in str(error)
    assert "\n" not in str(error)
    assert "\x00" not in str(error)
    assert "safe" in str(error)
    assert "forged" in str(error)


def test_error_sanitizes_every_legacy_runtime_error_argument() -> None:
    error = LLMError(
        "safe",
        7,
        {"x-api-key": "synthetic-mapping-secret"},
        b"synthetic-bytes-secret",
    )

    assert error.args[0:2] == ("safe", 7)
    rendered = str(error)
    assert "synthetic-mapping-secret" not in rendered
    assert "synthetic-bytes-secret" not in rendered
    assert "<redacted>" in rendered


def test_error_redacts_non_bearer_assignments_and_hostile_exception_args() -> None:
    assigned = LLMError(
        "auth=synthetic-auth api_key: synthetic-key "
        + "cookie=synthetic-cookie?token=synthetic-query"
    )
    hostile = LLMError(cast("object", HostileArgsError()))

    rendered = str(assigned)
    assert "synthetic-auth" not in rendered
    assert "synthetic-key" not in rendered
    assert "synthetic-cookie" not in rendered
    assert "synthetic-query" not in rendered
    assert hostile.args == ({"type": "HostileArgsError", "args": "<unavailable>"},)
