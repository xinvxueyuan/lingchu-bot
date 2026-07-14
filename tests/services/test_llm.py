from __future__ import annotations

import asyncio
from collections.abc import Iterator, Sequence
from importlib import import_module
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from typing import overload, override
from unittest.mock import AsyncMock, Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services import llm
from src.plugins.nonebot_plugin_lingchu_bot.services.llm import compat as llm_compat

LLM_PUBLIC_NAMES = {
    "CapabilityRegistry",
    "CapabilityResult",
    "ChatMessage",
    "EmptyLLMContentError",
    "LLMCallRecord",
    "LLMError",
    "LLMEvent",
    "LLMOptions",
    "LLMProfile",
    "LLMProviderError",
    "LLMResponse",
    "LLMRuntime",
    "LLMUsage",
    "MissingLLMContentError",
    "StructuredLLMObserver",
    "WebSearchResult",
    "complete_chat",
    "complete_with_web_search",
    "project_stream_event",
    "supports_web_search",
}


def test_llm_and_subplugin_contract_public_imports() -> None:
    public_llm = import_module("src.plugins.nonebot_plugin_lingchu_bot.services.llm")

    assert llm is public_llm
    assert set(public_llm.__all__) == LLM_PUBLIC_NAMES
    assert all(getattr(public_llm, name) is not None for name in public_llm.__all__)

    contracts = import_module(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.contracts"
    )

    assert all(getattr(contracts, name) is not None for name in contracts.__all__)


def test_isolated_facade_import_does_not_load_runtime_dependencies() -> None:
    """Load only the facade by replacing its real parent packages."""
    script = r"""
import builtins
import importlib
from importlib.abc import MetaPathFinder
from pathlib import Path
import sys
from types import ModuleType

root = Path.cwd()
package_paths = {
    "src": root / "src",
    "src.plugins": root / "src" / "plugins",
    "src.plugins.nonebot_plugin_lingchu_bot": (
        root / "src" / "plugins" / "nonebot_plugin_lingchu_bot"
    ),
    "src.plugins.nonebot_plugin_lingchu_bot.services": (
        root / "src" / "plugins" / "nonebot_plugin_lingchu_bot" / "services"
    ),
}
for name, path in package_paths.items():
    package = ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules[name] = package

class ForbiddenImportFinder(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "openai" or fullname.startswith("openai."):
            raise AssertionError(f"forbidden SDK import: {fullname}")
        if fullname == "litellm" or fullname.startswith("litellm."):
            raise AssertionError(f"forbidden SDK import: {fullname}")
        if fullname == "nonebot_plugin_localstore" or fullname.startswith(
            "nonebot_plugin_localstore."
        ):
            raise AssertionError(f"forbidden localstore import: {fullname}")
        if fullname.endswith(".core.runtime_config"):
            raise AssertionError(f"forbidden runtime config import: {fullname}")
        return None

original_open = builtins.open
def guarded_open(file, *args, **kwargs):
    if Path(file).name == "config.toml":
        raise AssertionError(f"forbidden config read: {file}")
    return original_open(file, *args, **kwargs)

sys.meta_path.insert(0, ForbiddenImportFinder())
builtins.open = guarded_open
module = importlib.import_module(
    "src.plugins.nonebot_plugin_lingchu_bot.services.llm"
)
assert set(module.__all__) == {
    "CapabilityRegistry",
    "CapabilityResult",
    "ChatMessage",
    "EmptyLLMContentError",
    "LLMCallRecord",
    "LLMError",
    "LLMEvent",
    "LLMOptions",
    "LLMProfile",
    "LLMProviderError",
    "LLMResponse",
    "LLMRuntime",
    "LLMUsage",
    "MissingLLMContentError",
    "StructuredLLMObserver",
    "WebSearchResult",
    "complete_chat",
    "complete_with_web_search",
    "project_stream_event",
    "supports_web_search",
}
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_normal_services_llm_import_does_not_load_provider_sdks() -> None:
    script = r"""
import importlib
from importlib.abc import MetaPathFinder
import sys

import nonebot

class ForbiddenSDKImportFinder(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "openai" or fullname.startswith("openai."):
            raise AssertionError(f"forbidden SDK import: {fullname}")
        if fullname == "litellm" or fullname.startswith("litellm."):
            raise AssertionError(f"forbidden SDK import: {fullname}")
        return None

sys.meta_path.insert(0, ForbiddenSDKImportFinder())
nonebot.init()
assert nonebot.load_plugin("src.plugins.nonebot_plugin_lingchu_bot") is not None
module = importlib.import_module(
    "src.plugins.nonebot_plugin_lingchu_bot.services.llm"
)
assert "complete_chat" in module.__all__
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def make_response(content: str | None = "hello") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


@pytest.fixture
def runtime_config() -> SimpleNamespace:
    return SimpleNamespace(
        ai_provider="litellm",
        ai_model="gpt-4o-mini",
        ai_base_url="https://example.test/v1",
        ai_api_key=None,
        ai_timeout=12.5,
    )


@pytest.fixture
def patched_runtime_config(
    monkeypatch: pytest.MonkeyPatch,
    runtime_config: SimpleNamespace,
) -> SimpleNamespace:
    monkeypatch.setattr(llm_compat, "runtime_config", runtime_config)
    return runtime_config


async def test_complete_chat_uses_litellm_provider(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    call_litellm = AsyncMock(return_value=make_response("lite"))
    backend = SimpleNamespace(call=call_litellm, close=AsyncMock())
    backend_factory = Mock(return_value=backend)
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", backend_factory)

    result = await llm.complete_chat([{"role": "user", "content": "hi"}])

    assert result == "lite"
    created_profile = backend_factory.call_args.args[0]
    assert created_profile.name == "__compat__"
    assert created_profile.backend == "litellm"
    assert created_profile.model == "gpt-4o-mini"
    assert created_profile.base_url == "https://example.test/v1"
    assert created_profile.timeout == 12.5
    assert backend_factory.call_args.kwargs == {"_forward_max_retries": False}
    call_litellm.assert_awaited_once_with(
        "acompletion",
        messages=[{"role": "user", "content": "hi"}],
    )
    backend.close.assert_awaited_once_with()


async def test_compat_litellm_call_does_not_inject_retry_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    async def acompletion(**params: object) -> SimpleNamespace:
        received.update(params)
        return make_response("native-boundary")

    module = ModuleType("litellm")
    module.__dict__["acompletion"] = acompletion
    monkeypatch.setitem(sys.modules, "litellm", module)
    options = llm.LLMOptions(
        "litellm",
        "openai/gpt-test",
        "https://gateway.example.test/v1",
        "compat-secret",
        13,
    )

    result = await llm.complete_chat(
        [{"role": "user", "content": "hello"}],
        options=options,
    )

    assert result == "native-boundary"
    assert received == {
        "model": "openai/gpt-test",
        "timeout": 13,
        "api_key": "compat-secret",
        "api_base": "https://gateway.example.test/v1",
        "messages": [{"role": "user", "content": "hello"}],
    }


async def test_complete_chat_uses_openai_provider(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    patched_runtime_config.ai_provider = "openai"
    create = AsyncMock(return_value=make_response("openai"))
    backend = SimpleNamespace(
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ),
        close=AsyncMock(),
    )
    backend_factory = Mock(return_value=backend)
    monkeypatch.setattr(llm_compat, "OpenAIBackend", backend_factory, raising=False)

    result = await llm.complete_chat([{"role": "user", "content": "hi"}])

    assert result == "openai"
    created_profile = backend_factory.call_args.args[0]
    assert created_profile.name == "__compat__"
    assert created_profile.backend == "openai"
    assert created_profile.model == "gpt-4o-mini"
    assert created_profile.base_url == "https://example.test/v1"
    assert created_profile.timeout == 12.5
    create.assert_awaited_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
    )
    backend.close.assert_awaited_once_with()


async def test_complete_chat_uses_explicit_options(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    create = AsyncMock(return_value=make_response("child"))
    backend = SimpleNamespace(
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ),
        close=AsyncMock(),
    )
    backend_factory = Mock(return_value=backend)
    monkeypatch.setattr(llm_compat, "OpenAIBackend", backend_factory)
    options = llm.LLMOptions(
        provider="openai",
        model="child-model",
        base_url="https://child.example/v1",
        api_key="child-key",
        timeout=7.0,
    )

    result = await llm.complete_chat(
        [{"role": "user", "content": "hi"}],
        options=options,
    )

    assert result == "child"
    assert patched_runtime_config.ai_provider == "litellm"
    created_profile = backend_factory.call_args.args[0]
    assert created_profile.api_key == "child-key"
    assert created_profile.base_url == "https://child.example/v1"
    create.assert_awaited_once_with(
        model="child-model",
        messages=[{"role": "user", "content": "hi"}],
    )
    backend.close.assert_awaited_once_with()


async def test_complete_chat_model_argument_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    call_litellm = AsyncMock(return_value=make_response("custom"))
    backend = SimpleNamespace(call=call_litellm, close=AsyncMock())
    backend_factory = Mock(return_value=backend)
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", backend_factory)

    result = await llm.complete_chat(
        [{"role": "user", "content": "hi"}],
        model="custom-model",
    )

    assert result == "custom"
    assert backend_factory.call_args.args[0].model == "custom-model"
    call_litellm.assert_awaited_once_with(
        "acompletion", messages=[{"role": "user", "content": "hi"}]
    )


async def test_explicit_options_are_request_scoped_without_named_cache_growth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[SimpleNamespace] = []

    def build_backend(
        _profile: object,
        *,
        _forward_max_retries: bool,
    ) -> SimpleNamespace:
        assert not _forward_max_retries
        backend = SimpleNamespace(
            call=AsyncMock(return_value=make_response("ephemeral")),
            close=AsyncMock(),
        )
        created.append(backend)
        return backend

    backend_factory = Mock(side_effect=build_backend)
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", backend_factory)
    options = llm.LLMOptions("litellm", "model", None, "secret", 10)

    await llm.complete_chat([{"role": "user", "content": "one"}], options=options)
    await llm.complete_chat([{"role": "user", "content": "two"}], options=options)

    assert len(created) == 2
    assert created[0] is not created[1]
    for backend in created:
        backend.close.assert_awaited_once_with()
    assert not hasattr(llm_compat, "_runtime")


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(choices=[]),
        make_response(None),
        make_response(""),
    ],
)
async def test_complete_chat_rejects_empty_content(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
    response: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    backend = SimpleNamespace(
        call=AsyncMock(return_value=response),
        close=AsyncMock(),
    )
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", Mock(return_value=backend))

    with pytest.raises(llm.LLMError):
        await llm.complete_chat([{"role": "user", "content": "hi"}])


async def test_complete_chat_wraps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    backend = SimpleNamespace(
        call=AsyncMock(side_effect=RuntimeError("provider down")),
        close=AsyncMock(),
    )
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", Mock(return_value=backend))

    with pytest.raises(llm.LLMError) as exc_info:
        await llm.complete_chat([{"role": "user", "content": "hi"}])

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_supports_web_search_requires_litellm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = Mock(return_value=True)
    monkeypatch.setattr(llm_compat, "probe_capability", probe)

    assert not llm.supports_web_search(
        llm.LLMOptions("openai", "gpt-5", None, "key", 10)
    )
    probe.assert_not_called()


def test_supports_web_search_uses_selected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = Mock(return_value=SimpleNamespace(support="supported"))
    backend = SimpleNamespace(release=Mock())
    backend_factory = Mock(return_value=backend)
    monkeypatch.setattr(llm_compat, "probe_capability", probe)
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", backend_factory)
    options = llm.LLMOptions("litellm", "openai/gpt-5", None, "key", 10)

    assert llm.supports_web_search(options)
    profile = probe.call_args.args[0]
    assert profile.model == "openai/gpt-5"
    assert profile.api_key == "key"
    assert probe.call_args.args[1] == "web_search"
    assert backend_factory.call_args.kwargs == {"_forward_max_retries": False}
    backend.release.assert_called_once_with()


def test_supports_web_search_soft_fails_probe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = SimpleNamespace(release=Mock())
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", Mock(return_value=backend))
    monkeypatch.setattr(
        llm_compat,
        "probe_capability",
        Mock(side_effect=RuntimeError("probe failed")),
    )

    assert not llm.supports_web_search(
        llm.LLMOptions("litellm", "openai/gpt-5", None, "key", 10)
    )
    backend.release.assert_called_once_with()


def test_supports_web_search_projects_unknown_to_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm_compat,
        "probe_capability",
        Mock(return_value=SimpleNamespace(support="unknown")),
    )

    assert not llm.supports_web_search(
        llm.LLMOptions("litellm", "openai/gpt-5", None, "key", 10)
    )


def make_search_response(
    content: str | None = "answer",
    *,
    annotations: object = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, annotations=annotations),
            )
        ]
    )


class RaisingAnnotations(Sequence[object]):
    @overload
    def __getitem__(self, index: int) -> object: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[object]: ...

    @override
    def __getitem__(self, index: int | slice) -> object | Sequence[object]:
        raise RuntimeError

    @override
    def __len__(self) -> int:
        return 1

    @override
    def __iter__(self) -> Iterator[object]:
        raise RuntimeError


class RaisingMessage:
    content = "answer"

    @property
    def annotations(self) -> object:
        raise RuntimeError


async def test_complete_with_web_search_returns_content_and_ordered_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    options = llm.LLMOptions(
        "litellm", "openai/gpt-5", "https://example.test", "secret", 10
    )
    monkeypatch.setattr(llm_compat, "supports_web_search", Mock(return_value=True))
    response = make_search_response(
        annotations=[
            {"type": "url_citation", "url_citation": {"url": "https://a.test"}},
            SimpleNamespace(
                type="url_citation",
                url_citation=SimpleNamespace(url="https://b.test"),
            ),
            {"type": "url_citation", "url": "https://a.test"},
            {"unknown": "shape"},
        ]
    )
    call = AsyncMock(return_value=response)
    backend = SimpleNamespace(call=call, close=AsyncMock())
    backend_factory = Mock(return_value=backend)
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", backend_factory)

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "latest"}], options=options
    )

    assert result == llm.WebSearchResult(
        text="answer", sources=("https://a.test", "https://b.test")
    )
    created_profile = backend_factory.call_args.args[0]
    assert created_profile.model == "openai/gpt-5"
    assert created_profile.base_url == "https://example.test"
    assert created_profile.api_key == "secret"
    call.assert_awaited_once_with(
        "acompletion",
        messages=[{"role": "user", "content": "latest"}],
        tools=[{"type": "web_search"}],
    )
    backend.close.assert_awaited_once_with()


async def test_complete_with_web_search_finishes_close_before_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_started = asyncio.Event()
    close_started = asyncio.Event()
    allow_close = asyncio.Event()

    async def call(_operation: str, **_params: object) -> object:
        call_started.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    async def close() -> None:
        close_started.set()
        await allow_close.wait()

    backend = SimpleNamespace(call=call, close=close)
    monkeypatch.setattr(llm_compat, "supports_web_search", Mock(return_value=True))
    monkeypatch.setattr(
        llm_compat,
        "LiteLLMBackend",
        Mock(return_value=backend),
    )
    task = asyncio.create_task(
        llm.complete_with_web_search(
            [{"role": "user", "content": "latest"}],
            options=llm.LLMOptions("litellm", "model", None, "key", 10),
        )
    )
    await call_started.wait()

    task.cancel()
    await close_started.wait()
    assert not task.done()
    allow_close.set()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.parametrize(
    "message",
    [
        SimpleNamespace(content="answer", annotations=RaisingAnnotations()),
        RaisingMessage(),
    ],
)
async def test_complete_with_web_search_ignores_hostile_annotation_shapes(
    monkeypatch: pytest.MonkeyPatch,
    message: object,
) -> None:
    monkeypatch.setattr(llm_compat, "supports_web_search", Mock(return_value=True))
    backend = SimpleNamespace(
        call=AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
            )
        ),
        close=AsyncMock(),
    )
    monkeypatch.setattr(
        llm_compat,
        "LiteLLMBackend",
        Mock(return_value=backend),
    )

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "latest"}],
        options=llm.LLMOptions("litellm", "model", None, "key", 10),
    )

    assert result == llm.WebSearchResult(text="answer", sources=())


async def test_complete_with_web_search_rejects_unsafe_source_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm_compat, "supports_web_search", Mock(return_value=True))
    response = make_search_response(
        annotations=[
            {"url": "javascript:alert(1)"},
            {"url": "https://user:password@example.test/private"},
            {"url": "https://safe.example/source#api-key=secret"},
            {"url": "https://safe.example/source?api_key=secret"},
            {"url": "https://safe.example/source?next=Bearer%20secret"},
            {"url": "http://127.0.0.1/private"},
            {"url": "http://169.254.169.254/latest/meta-data"},
            {"url": "http://metadata.google.internal/computeMetadata/v1"},
            {"url": "https://service.localhost/private"},
            {"url": "https://safe.example/source?lang=en&page=2"},
            {"url": "https://safe.example/source"},
        ]
    )
    backend = SimpleNamespace(
        call=AsyncMock(return_value=response),
        close=AsyncMock(),
    )
    monkeypatch.setattr(llm_compat, "LiteLLMBackend", Mock(return_value=backend))

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "latest"}],
        options=llm.LLMOptions("litellm", "model", None, "key", 10),
    )

    assert result == llm.WebSearchResult(
        text="answer",
        sources=(
            "https://safe.example/source?lang=en&page=2",
            "https://safe.example/source",
        ),
    )


async def test_complete_with_web_search_returns_none_when_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm_compat, "supports_web_search", Mock(return_value=False))
    call = AsyncMock()
    monkeypatch.setattr(
        llm_compat,
        "LiteLLMBackend",
        Mock(return_value=SimpleNamespace(call=call, close=AsyncMock())),
    )

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "latest"}],
        options=llm.LLMOptions("litellm", "model", None, "key", 10),
    )

    assert result is None
    call.assert_not_awaited()


@pytest.mark.parametrize("content", [None, ""])
async def test_complete_with_web_search_returns_none_for_empty_content(
    monkeypatch: pytest.MonkeyPatch,
    content: str | None,
) -> None:
    monkeypatch.setattr(llm_compat, "supports_web_search", Mock(return_value=True))
    monkeypatch.setattr(
        llm_compat,
        "LiteLLMBackend",
        Mock(
            return_value=SimpleNamespace(
                call=AsyncMock(return_value=make_search_response(content)),
                close=AsyncMock(),
            )
        ),
    )

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "latest"}],
        options=llm.LLMOptions("litellm", "model", None, "key", 10),
    )

    assert result is None


async def test_complete_with_web_search_soft_fails_without_logging_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "super-secret-api-key"
    monkeypatch.setattr(llm_compat, "supports_web_search", Mock(return_value=True))
    monkeypatch.setattr(
        llm_compat,
        "LiteLLMBackend",
        Mock(
            return_value=SimpleNamespace(
                call=AsyncMock(side_effect=RuntimeError(f"provider exposed {secret}")),
                close=AsyncMock(),
            )
        ),
    )
    warning = Mock()
    monkeypatch.setattr(llm_compat.logger, "warning", warning)

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "private prompt"}],
        options=llm.LLMOptions("litellm", "model", None, secret, 10),
    )

    assert result is None
    assert secret not in str(warning.call_args)
    assert "private prompt" not in str(warning.call_args)
