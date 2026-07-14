from __future__ import annotations

from collections.abc import Mapping, Sequence
import sys
from types import ModuleType
from typing import override

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.backends import (
    _NO_CREDENTIAL_API_KEY,
    LiteLLMBackend,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile


def profile(**provider_options: object) -> LLMProfile:
    return LLMProfile(
        name="default",
        backend="litellm",
        model="openai/gpt-4o-mini",
        provider_options=provider_options,
    )


def test_sdk_is_lazy_and_preserves_native_module_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("litellm")
    monkeypatch.setitem(sys.modules, "litellm", module)
    backend = LiteLLMBackend(profile())

    assert backend._sdk is None
    assert backend.sdk is module
    assert backend.sdk is module


def test_missing_dependency_is_distinguished_from_transitive_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "litellm", raising=False)
    original_import = __import__

    def import_missing_litellm(
        name: str,
        globals_: Mapping[str, object] | None = None,
        locals_: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = None,
        level: int = 0,
    ) -> ModuleType:
        if name == "litellm":
            raise ModuleNotFoundError(name="litellm")
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr("builtins.__import__", import_missing_litellm)
    with pytest.raises(ModuleNotFoundError, match="optional 'litellm' dependency"):
        _ = LiteLLMBackend(profile()).sdk

    def import_with_missing_transitive(
        name: str,
        globals_: Mapping[str, object] | None = None,
        locals_: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = None,
        level: int = 0,
    ) -> ModuleType:
        if name == "litellm":
            raise ModuleNotFoundError(name="pydantic_core")
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr("builtins.__import__", import_with_missing_transitive)
    with pytest.raises(ModuleNotFoundError) as exc_info:
        _ = LiteLLMBackend(profile()).sdk
    assert exc_info.value.name == "pydantic_core"


@pytest.mark.asyncio
async def test_call_preserves_native_return_and_exception_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_response = object()
    native_error = RuntimeError("provider failure")

    async def aresponses(**params: object) -> object:
        assert params == {
            "model": "configured",
            "timeout": 60.0,
            "max_retries": 2,
            "api_key": _NO_CREDENTIAL_API_KEY,
            "input": "hello",
        }
        return native_response

    async def afailing(**params: object) -> object:
        assert params == {
            "model": "configured",
            "timeout": 60.0,
            "max_retries": 2,
            "api_key": _NO_CREDENTIAL_API_KEY,
        }
        raise native_error

    module = ModuleType("litellm")
    module.__dict__["aresponses"] = aresponses
    module.__dict__["afailing"] = afailing
    monkeypatch.setitem(sys.modules, "litellm", module)
    backend = LiteLLMBackend(profile(model="configured"))

    assert await backend.call("aresponses", input="hello") is native_response
    with pytest.raises(RuntimeError) as exc_info:
        await backend.call("afailing")
    assert exc_info.value is native_error


@pytest.mark.asyncio
async def test_call_merges_defaults_without_mutating_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    async def acompletion(**params: object) -> object:
        received.update(params)
        nested = params["nested"]
        assert isinstance(nested, dict)
        nested["x"] = 2
        return object()

    module = ModuleType("litellm")
    module.__dict__["acompletion"] = acompletion
    monkeypatch.setitem(sys.modules, "litellm", module)
    defaults = {"model": "configured", "temperature": 0.2, "nested": {"x": 1}}
    caller = {"temperature": 0.8, "messages": [{"role": "user"}]}
    backend = LiteLLMBackend(profile(**defaults))

    await backend.call("acompletion", **caller)

    assert received == {
        "model": "configured",
        "timeout": 60.0,
        "max_retries": 2,
        "api_key": _NO_CREDENTIAL_API_KEY,
        "temperature": 0.8,
        "nested": {"x": 2},
        "messages": [{"role": "user"}],
    }
    assert defaults == {
        "model": "configured",
        "temperature": 0.2,
        "nested": {"x": 1},
    }
    assert caller == {"temperature": 0.8, "messages": [{"role": "user"}]}


@pytest.mark.asyncio
async def test_call_does_not_delegate_missing_key_to_provider_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    async def acompletion(**params: object) -> object:
        received.update(params)
        return object()

    module = ModuleType("litellm")
    module.__dict__["acompletion"] = acompletion
    monkeypatch.setitem(sys.modules, "litellm", module)
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-secret")

    await LiteLLMBackend(profile()).call("acompletion")

    assert received["api_key"] == _NO_CREDENTIAL_API_KEY


@pytest.mark.asyncio
async def test_call_projects_profile_defaults_and_caller_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    async def acompletion(**params: object) -> object:
        received.update(params)
        return object()

    module = ModuleType("litellm")
    module.__dict__["acompletion"] = acompletion
    monkeypatch.setitem(sys.modules, "litellm", module)
    backend = LiteLLMBackend(
        LLMProfile(
            name="configured",
            backend="litellm",
            model="openai/gpt-4o-mini",
            api_key="profile-secret",
            base_url="https://gateway.example.test",
            timeout=12,
            max_retries=3,
            default_headers={"x-profile": "not-forwarded-without-sdk-contract"},
            default_query={"tenant": "not-forwarded-without-sdk-contract"},
            organization="org",
            project="project",
        )
    )

    await backend.call(
        "acompletion",
        model="caller-model",
        timeout=5,
        max_retries=1,
        api_key="caller-secret",
        api_base="https://caller.example.test",
    )

    assert received == {
        "model": "caller-model",
        "timeout": 5,
        "max_retries": 1,
        "api_key": "caller-secret",
        "api_base": "https://caller.example.test",
        "extra_headers": {"x-profile": "not-forwarded-without-sdk-contract"},
        "extra_query": {"tenant": "not-forwarded-without-sdk-contract"},
        "organization": "org",
        "project": "project",
    }


@pytest.mark.asyncio
async def test_repeated_failures_raise_fresh_validation_exceptions() -> None:
    backend = LiteLLMBackend(profile())

    failures: list[ValueError] = []
    for _ in range(2):
        with pytest.raises(ValueError) as exc_info:
            await backend.call("_private")
        failures.append(exc_info.value)

    assert failures[0] is not failures[1]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    ["", "_private", "__dunder__", "with.dot", "slash/name", "back\\slash"],
)
async def test_call_rejects_non_public_or_multisegment_names_before_lookup(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    class TrapModule(ModuleType):
        @override
        def __getattr__(self, name: str) -> object:
            raise AssertionError(name)

    monkeypatch.setitem(sys.modules, "litellm", TrapModule("litellm"))
    backend = LiteLLMBackend(profile())

    with pytest.raises(ValueError, match="invalid LiteLLM operation"):
        await backend.call(operation)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["missing", "non_callable", "synchronous"])
async def test_call_rejects_missing_noncallable_and_sync_operations_without_invocation(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    calls = 0
    module = ModuleType("litellm")
    if kind == "non_callable":
        module.__dict__["operation"] = object()
    elif kind == "synchronous":

        def operation() -> object:
            nonlocal calls
            calls += 1
            return object()

        module.__dict__["operation"] = operation
    monkeypatch.setitem(sys.modules, "litellm", module)

    with pytest.raises(TypeError, match="must be asynchronous"):
        await LiteLLMBackend(profile()).call("operation")
    assert calls == 0


@pytest.mark.asyncio
async def test_close_is_idempotent_and_forbids_new_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("litellm")
    monkeypatch.setitem(sys.modules, "litellm", module)
    backend = LiteLLMBackend(profile())
    assert backend.sdk is module

    await backend.close()
    await backend.close()

    with pytest.raises(RuntimeError, match="closed"):
        _ = backend.sdk
    with pytest.raises(RuntimeError, match="closed"):
        _ = backend.router
