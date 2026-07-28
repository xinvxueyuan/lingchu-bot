"""Tests for the model-string capability heuristic in ``CapabilityRegistry``."""

from collections.abc import Iterator
from typing import Literal, cast

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.capabilities import (
    CapabilityRegistry,
    CapabilityResult,
    invalidate_capability_cache,
    probe_capability,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile


def _profile(model: str = "openai:gpt-5.2") -> LLMProfile:
    """Build a Pydantic AI profile with the simplified constructor."""
    return LLMProfile(
        name="default",
        backend="pydantic_ai",
        model=model,
        base_url=None,
        api_key=None,
        timeout=60.0,
        max_retries=2,
    )


@pytest.fixture(autouse=True)
def _reset_default_registry() -> Iterator[None]:
    """Isolate the process-global default registry between tests."""
    invalidate_capability_cache()
    yield
    invalidate_capability_cache()


@pytest.mark.parametrize(
    "model",
    [
        "openai:gpt-5.2",
        "anthropic:claude-opus-4",
        "google-gla:gemini-2.5-pro",
        "google-vertex:gemini-2.5-pro",
    ],
)
def test_known_model_prefix_probes_supported(model: str) -> None:
    profile = _profile(model)

    result = probe_capability(profile, "web_search", backend=None)

    assert result == CapabilityResult(
        capability="web_search",
        support="supported",
        source="pydantic_ai.model_string",
        reason=None,
    )


def test_unknown_model_prefix_probes_unknown_with_model_reason() -> None:
    profile = _profile("foo:bar")

    result = probe_capability(profile, "web_search", backend=None)

    assert result.capability == "web_search"
    assert result.support == "unknown"
    assert result.source == "pydantic_ai.model_string"
    assert result.reason == "model_capability_not_authoritative"


def test_unsupported_capability_name_probes_unknown_with_capability_reason() -> None:
    profile = _profile("openai:gpt-5.2")

    result = probe_capability(
        profile, cast('Literal["web_search"]', "tool_use"), backend=None
    )

    assert result.capability == "tool_use"
    assert result.support == "unknown"
    assert result.source == "pydantic_ai.model_string"
    assert result.reason == "capability_not_authoritative"


def test_registry_caches_repeated_probe_results() -> None:
    registry = CapabilityRegistry()
    profile = _profile("openai:gpt-5.2")

    first = registry.probe(profile, "web_search", backend=None)
    second = registry.probe(profile, "web_search", backend=None)

    assert first is second


def test_registry_invalidate_clears_cache_so_reprobe_returns_new_instance() -> None:
    registry = CapabilityRegistry()
    profile = _profile("openai:gpt-5.2")

    first = registry.probe(profile, "web_search", backend=None)
    registry.invalidate()
    second = registry.probe(profile, "web_search", backend=None)

    assert first is not second
    assert first == second


def test_invalidate_capability_cache_clears_process_level_registry() -> None:
    profile = _profile("openai:gpt-5.2")

    first = probe_capability(profile, "web_search", backend=None)
    invalidate_capability_cache()
    second = probe_capability(profile, "web_search", backend=None)

    assert first is not second
    assert first == second


def test_probe_capability_delegates_to_default_registry() -> None:
    profile = _profile("openai:gpt-5.2")

    result = probe_capability(profile, "web_search", backend=None)

    assert result.support == "supported"
    assert result.source == "pydantic_ai.model_string"


def test_backend_parameter_is_ignored() -> None:
    profile = _profile("openai:gpt-5.2")

    result = probe_capability(profile, "web_search", backend=object())

    assert result.support == "supported"
