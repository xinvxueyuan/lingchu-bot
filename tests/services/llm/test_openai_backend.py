from __future__ import annotations

from collections.abc import Mapping, Sequence
import sys
import threading
import time
from types import ModuleType
from unittest.mock import Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.backends import (
    _NO_CREDENTIAL_API_KEY,
    OpenAIBackend,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile


def profile() -> LLMProfile:
    return LLMProfile(
        name="default",
        backend="openai",
        model="gpt",
        api_key="secret",
        base_url="https://example.test",
        organization="org",
        project="proj",
        timeout=12,
        max_retries=3,
        default_headers={"x": "y"},
        default_query={"q": "v"},
    )


def test_lazy_import_and_constructor(monkeypatch: pytest.MonkeyPatch) -> None:
    constructor = Mock(return_value=Mock())
    monkeypatch.setitem(sys.modules, "openai", ModuleType("openai"))
    monkeypatch.setattr(
        sys.modules["openai"], "AsyncOpenAI", constructor, raising=False
    )
    backend = OpenAIBackend(profile())
    constructor.assert_not_called()
    client = backend.client
    assert client is constructor.return_value
    constructor.assert_called_once_with(
        api_key="secret",
        base_url="https://example.test",
        organization="org",
        project="proj",
        timeout=12,
        max_retries=3,
        default_headers={"x": "y"},
        default_query={"q": "v"},
    )


def test_real_sdk_does_not_adopt_ambient_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-secret")
    backend = OpenAIBackend(
        LLMProfile(
            name="custom",
            backend="openai",
            model="gpt",
            base_url="https://custom.example/v1",
        )
    )

    assert backend.client.api_key == _NO_CREDENTIAL_API_KEY

    import asyncio

    asyncio.run(backend.close())


@pytest.mark.asyncio
async def test_close_idempotent_and_rejects_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    client.close = Mock()
    module = ModuleType("openai")
    setattr(module, "Async" + "OpenAI", Mock(return_value=client))
    monkeypatch.setitem(sys.modules, "openai", module)
    backend = OpenAIBackend(profile())
    assert backend.client is client
    await backend.close()
    await backend.close()
    client.close.assert_called_once_with()
    failures: list[RuntimeError] = []
    for _ in range(2):
        with pytest.raises(RuntimeError) as exc_info:
            _ = backend.client
        failures.append(exc_info.value)
    assert failures[0] is not failures[1]


def test_missing_openai_dependency_is_distinguished_from_transitive_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "openai", raising=False)
    original_import = __import__

    def import_missing_openai(
        name: str,
        globals_: Mapping[str, object] | None = None,
        locals_: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = None,
        level: int = 0,
    ) -> ModuleType:
        if name == "openai":
            raise ModuleNotFoundError(name="openai")
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr("builtins.__import__", import_missing_openai)
    backend = OpenAIBackend(profile())
    with pytest.raises(ModuleNotFoundError, match="optional 'openai' dependency"):
        _ = backend.client

    def import_with_missing_transitive(
        name: str,
        globals_: Mapping[str, object] | None = None,
        locals_: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = None,
        level: int = 0,
    ) -> ModuleType:
        if name == "openai":
            raise ModuleNotFoundError(name="httpx")
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr("builtins.__import__", import_with_missing_transitive)
    with pytest.raises(ModuleNotFoundError) as exc_info:
        _ = OpenAIBackend(profile()).client
    assert exc_info.value.name == "httpx"


def test_with_options_preserves_native_sdk_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    configured = Mock()
    client.with_options.return_value = configured
    module = ModuleType("openai")
    setattr(module, "Async" + "OpenAI", Mock(return_value=client))
    monkeypatch.setitem(sys.modules, "openai", module)
    backend = OpenAIBackend(profile())

    assert backend.with_options(stream=True) is configured
    assert backend.client is client
    client.with_options.assert_called_once_with(stream=True)
    module.AsyncOpenAI.assert_called_once()


def test_profile_rotation_replaces_client_and_closes_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients = [Mock(), Mock()]
    constructor = Mock(side_effect=clients)
    module = ModuleType("openai")
    setattr(module, "Async" + "OpenAI", constructor)
    monkeypatch.setitem(sys.modules, "openai", module)
    backend = OpenAIBackend(profile())

    assert backend.client is clients[0]
    backend.profile = profile().__class__(
        name="rotated",
        backend="openai",
        model="gpt-4o",
        api_key="rotated-secret",
    )
    assert backend.client is clients[1]
    assert constructor.call_count == 2

    import asyncio

    asyncio.run(backend.close())
    clients[0].close.assert_called_once_with()
    clients[1].close.assert_called_once_with()


def test_concurrent_client_acquisition_constructs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor = Mock(side_effect=lambda **_: (time.sleep(0.02), Mock())[1])
    module = ModuleType("openai")
    setattr(module, "Async" + "OpenAI", constructor)
    monkeypatch.setitem(sys.modules, "openai", module)
    backend = OpenAIBackend(profile())
    results: list[object] = []
    barrier = threading.Barrier(8)

    def acquire() -> None:
        barrier.wait()
        results.append(backend.client)

    threads = [threading.Thread(target=acquire) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert constructor.call_count == 1
    assert len({id(client) for client in results}) == 1


@pytest.mark.asyncio
async def test_close_continues_after_one_client_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second = Mock(), Mock()
    first.close.side_effect = RuntimeError("first close failed")
    constructor = Mock(side_effect=[first, second])
    module = ModuleType("openai")
    setattr(module, "Async" + "OpenAI", constructor)
    monkeypatch.setitem(sys.modules, "openai", module)
    backend = OpenAIBackend(profile())
    _ = backend.client
    backend.profile = profile().__class__(
        name="rotated",
        backend="openai",
        model="gpt-4o",
        api_key="rotated-secret",
    )
    _ = backend.client

    await backend.close()
    first.close.assert_called_once_with()
    second.close.assert_called_once_with()
