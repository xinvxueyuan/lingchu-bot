import threading
from types import SimpleNamespace
from unittest.mock import Mock

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.capabilities import (
    CapabilityRegistry,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile


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
