from collections.abc import Iterator
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.capabilities import (
    CapabilityRegistry,
    invalidate_capability_cache,
    probe_capability,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile


@pytest.fixture(autouse=True)
def _reset_default_registry() -> Iterator[None]:
    """Isolate process-global default registry between tests."""
    invalidate_capability_cache()
    yield
    invalidate_capability_cache()


class _HostileSDKAccessError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("dependency path leaked")


def test_litellm_native_probe_reports_supported() -> None:
    probe = Mock(return_value=True)
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=probe)
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.capability == "web_search"
    assert result.support == "supported"
    assert result.source == "litellm.supports_web_search"
    assert result.reason is None
    probe.assert_called_once_with(model="openai/gpt-test")


def test_litellm_native_probe_reports_unsupported() -> None:
    backend = SimpleNamespace(
        sdk=SimpleNamespace(
            __version__="test-sdk", supports_web_search=Mock(return_value=False)
        )
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unsupported"
    assert result.reason is None


def test_probe_exception_is_unknown_instead_of_unsupported() -> None:
    backend = SimpleNamespace(
        sdk=SimpleNamespace(
            __version__="test-sdk",
            supports_web_search=Mock(side_effect=RuntimeError("provider body")),
        )
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "probe_error"
    assert "provider body" not in repr(result)


def test_backend_sdk_access_failure_is_unknown() -> None:
    class BrokenBackend:
        @property
        def sdk(self) -> object:
            raise _HostileSDKAccessError

    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=BrokenBackend())

    assert result.support == "unknown"
    assert result.reason == "probe_error"
    assert "dependency path leaked" not in repr(result)


def test_openai_operation_presence_does_not_claim_model_support() -> None:
    backend = SimpleNamespace(
        client=SimpleNamespace(responses=SimpleNamespace(create=Mock()))
    )
    profile = LLMProfile("compat", "openai", "gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "model_support_not_authoritative"


def test_cache_does_not_vary_with_or_retain_api_key() -> None:
    probe = Mock(return_value=True)
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=probe)
    )
    registry = CapabilityRegistry()
    first = LLMProfile("compat", "litellm", "openai/gpt-test", api_key="first-secret")
    rotated = LLMProfile(
        "compat", "litellm", "openai/gpt-test", api_key="second-secret"
    )

    registry.probe(first, "web_search", backend=backend)
    registry.probe(rotated, "web_search", backend=backend)

    probe.assert_called_once_with(model="openai/gpt-test")
    assert "first-secret" not in repr(registry)
    assert "second-secret" not in repr(registry)


def test_configuration_reload_invalidation_reprobes() -> None:
    probe = Mock(side_effect=[True, False])
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=probe)
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")
    registry = CapabilityRegistry()

    assert registry.probe(profile, "web_search", backend=backend).support == "supported"
    registry.invalidate()

    assert (
        registry.probe(profile, "web_search", backend=backend).support == "unsupported"
    )
    assert probe.call_count == 2


def test_inflight_probe_cannot_publish_after_invalidation() -> None:
    probe_started = threading.Event()
    release_probe = threading.Event()
    results: list[str] = []
    invocation_count = 0

    def blocking_probe(*, model: str) -> bool:
        nonlocal invocation_count
        assert model == "openai/gpt-test"
        invocation_count += 1
        if invocation_count == 1:
            probe_started.set()
            assert release_probe.wait(timeout=5)
            return True
        return False

    probe = Mock(side_effect=blocking_probe)
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=probe)
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")
    registry = CapabilityRegistry()

    worker = threading.Thread(
        target=lambda: results.append(
            registry.probe(profile, "web_search", backend=backend).support
        )
    )
    worker.start()
    assert probe_started.wait(timeout=5)
    registry.invalidate()
    release_probe.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert results == ["supported"]
    assert (
        registry.probe(profile, "web_search", backend=backend).support == "unsupported"
    )
    assert probe.call_count == 2


class _HostileVersionAttributeSDK:
    """SDK whose ``__version__`` property raises to exercise fail-closed path."""

    @property
    def __version__(self) -> str:
        raise RuntimeError("version access hostile")


class _HostileProbeAttributeSDK:
    """SDK whose ``supports_web_search`` property raises during attribute access."""

    __version__ = "test-sdk"

    @property
    def supports_web_search(self) -> object:
        raise RuntimeError("probe attribute access hostile")


def test_sdk_version_returns_unknown_when_attribute_access_raises() -> None:
    """Lines 38-39: ``getattr(sdk, '__version__')`` raising -> 'unknown'."""
    backend = SimpleNamespace(sdk=_HostileVersionAttributeSDK())
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "probe_unavailable"
    assert "version access hostile" not in repr(result)


def test_sdk_version_falls_back_to_litellm_package_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Line 46: ``__version__`` non-str resolves via ``importlib.metadata.version``."""
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.services.llm.capabilities.version",
        lambda _name: "1.2.3-mocked",
    )
    backend = SimpleNamespace(sdk=SimpleNamespace(__version__=12345))
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "probe_unavailable"


def test_sdk_version_returns_unknown_when_litellm_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lines 44-45: ``__version__`` non-str and litellm missing -> 'unknown'."""
    from importlib.metadata import PackageNotFoundError

    def _missing(_name: str) -> str:
        raise PackageNotFoundError(_name)

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.services.llm.capabilities.version",
        _missing,
    )
    backend = SimpleNamespace(sdk=SimpleNamespace(__version__=12345))
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "probe_unavailable"


def test_probe_attribute_access_failure_treated_as_unavailable() -> None:
    """Lines 96-97: ``getattr(sdk, 'supports_web_search')`` raising -> probe=None."""
    backend = SimpleNamespace(sdk=_HostileProbeAttributeSDK())
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "probe_unavailable"
    assert "probe attribute access hostile" not in repr(result)


def test_probe_non_callable_attribute_returns_unavailable() -> None:
    """Line 99: ``supports_web_search`` present but non-callable -> 'probe_unavailable'."""
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search="not-callable")
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "probe_unavailable"


def test_probe_none_attribute_returns_unavailable() -> None:
    """Line 99: ``supports_web_search`` resolves to None -> 'probe_unavailable'."""
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=None)
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = CapabilityRegistry().probe(profile, "web_search", backend=backend)

    assert result.support == "unknown"
    assert result.reason == "probe_unavailable"


def test_module_level_probe_capability_delegates_to_default_registry() -> None:
    """Line 151: module-level ``probe_capability`` delegates to the default registry."""
    probe = Mock(return_value=True)
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=probe)
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    result = probe_capability(profile, "web_search", backend=backend)

    assert result.support == "supported"
    assert result.source == "litellm.supports_web_search"
    probe.assert_called_once_with(model="openai/gpt-test")


def test_module_level_invalidate_capability_cache_clears_default_registry() -> None:
    """Line 156: module-level ``invalidate_capability_cache`` clears cached probes."""
    probe = Mock(side_effect=[True, False])
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=probe)
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")

    first = probe_capability(profile, "web_search", backend=backend)
    assert first.support == "supported"

    invalidate_capability_cache()

    second = probe_capability(profile, "web_search", backend=backend)
    assert second.support == "unsupported"
    assert probe.call_count == 2


def test_probe_returns_cached_result_on_repeated_calls() -> None:
    """Cache hit path exercises ``_cache.setdefault`` after a successful probe."""
    probe = Mock(return_value=True)
    backend = SimpleNamespace(
        sdk=SimpleNamespace(__version__="test-sdk", supports_web_search=probe)
    )
    profile = LLMProfile("compat", "litellm", "openai/gpt-test")
    registry = CapabilityRegistry()

    first = registry.probe(profile, "web_search", backend=backend)
    second = registry.probe(profile, "web_search", backend=backend)

    assert first is second
    assert probe.call_count == 1
