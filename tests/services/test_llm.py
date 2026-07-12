from __future__ import annotations

from collections.abc import Iterator, Sequence
from types import SimpleNamespace
from typing import overload
from unittest.mock import AsyncMock, Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services import llm


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
    monkeypatch.setattr(llm, "runtime_config", runtime_config)
    return runtime_config


async def test_complete_chat_uses_litellm_provider(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    call_litellm = AsyncMock(return_value=make_response("lite"))
    monkeypatch.setattr(llm, "_call_litellm", call_litellm)

    result = await llm.complete_chat([{"role": "user", "content": "hi"}])

    assert result == "lite"
    call_litellm.assert_awaited_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        api_base="https://example.test/v1",
        api_key=None,
        request_timeout=12.5,
    )


async def test_complete_chat_uses_openai_provider(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    patched_runtime_config.ai_provider = "openai"
    call_openai = AsyncMock(return_value=make_response("openai"))
    monkeypatch.setattr(llm, "_call_openai", call_openai)

    result = await llm.complete_chat([{"role": "user", "content": "hi"}])

    assert result == "openai"
    call_openai.assert_awaited_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        base_url="https://example.test/v1",
        api_key=None,
        request_timeout=12.5,
    )


async def test_complete_chat_uses_explicit_options(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    call_openai = AsyncMock(return_value=make_response("child"))
    monkeypatch.setattr(llm, "_call_openai", call_openai)
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
    call_openai.assert_awaited_once_with(
        model="child-model",
        messages=[{"role": "user", "content": "hi"}],
        base_url="https://child.example/v1",
        api_key="child-key",
        request_timeout=7.0,
    )


async def test_complete_chat_model_argument_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    call_litellm = AsyncMock(return_value=make_response("custom"))
    monkeypatch.setattr(llm, "_call_litellm", call_litellm)

    result = await llm.complete_chat(
        [{"role": "user", "content": "hi"}],
        model="custom-model",
    )

    assert result == "custom"
    assert call_litellm.await_args is not None
    assert call_litellm.await_args.kwargs["model"] == "custom-model"


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
    monkeypatch.setattr(llm, "_call_litellm", AsyncMock(return_value=response))

    with pytest.raises(llm.LLMError):
        await llm.complete_chat([{"role": "user", "content": "hi"}])


async def test_complete_chat_wraps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    monkeypatch.setattr(
        llm,
        "_call_litellm",
        AsyncMock(side_effect=RuntimeError("provider down")),
    )

    with pytest.raises(llm.LLMError) as exc_info:
        await llm.complete_chat([{"role": "user", "content": "hi"}])

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_supports_web_search_requires_litellm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = Mock(return_value=True)
    monkeypatch.setattr(llm, "_litellm_supports_web_search", probe, raising=False)

    assert not llm.supports_web_search(
        llm.LLMOptions("openai", "gpt-5", None, "key", 10)
    )
    probe.assert_not_called()


def test_supports_web_search_uses_selected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = Mock(return_value=True)
    monkeypatch.setattr(llm, "_litellm_supports_web_search", probe, raising=False)
    options = llm.LLMOptions("litellm", "openai/gpt-5", None, "key", 10)

    assert llm.supports_web_search(options)
    probe.assert_called_once_with("openai/gpt-5")


def test_supports_web_search_soft_fails_probe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm,
        "_litellm_supports_web_search",
        Mock(side_effect=RuntimeError("probe failed")),
        raising=False,
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

    def __getitem__(self, index: int | slice) -> object | Sequence[object]:
        raise RuntimeError

    def __len__(self) -> int:
        return 1

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
    monkeypatch.setattr(llm, "supports_web_search", Mock(return_value=True))
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
    monkeypatch.setattr(llm, "_call_litellm_web_search", call, raising=False)

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "latest"}], options=options
    )

    assert result == llm.WebSearchResult(
        text="answer", sources=("https://a.test", "https://b.test")
    )
    call.assert_awaited_once_with(
        model="openai/gpt-5",
        messages=[{"role": "user", "content": "latest"}],
        api_base="https://example.test",
        api_key="secret",
        request_timeout=10,
    )


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
    monkeypatch.setattr(llm, "supports_web_search", Mock(return_value=True))
    monkeypatch.setattr(
        llm,
        "_call_litellm_web_search",
        AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
            )
        ),
    )

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "latest"}],
        options=llm.LLMOptions("litellm", "model", None, "key", 10),
    )

    assert result == llm.WebSearchResult(text="answer", sources=())


async def test_complete_with_web_search_returns_none_when_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "supports_web_search", Mock(return_value=False))
    call = AsyncMock()
    monkeypatch.setattr(llm, "_call_litellm_web_search", call, raising=False)

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
    monkeypatch.setattr(llm, "supports_web_search", Mock(return_value=True))
    monkeypatch.setattr(
        llm,
        "_call_litellm_web_search",
        AsyncMock(return_value=make_search_response(content)),
        raising=False,
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
    monkeypatch.setattr(llm, "supports_web_search", Mock(return_value=True))
    monkeypatch.setattr(
        llm,
        "_call_litellm_web_search",
        AsyncMock(side_effect=RuntimeError(f"provider exposed {secret}")),
        raising=False,
    )
    warning = Mock()
    monkeypatch.setattr(llm.logger, "warning", warning)

    result = await llm.complete_with_web_search(
        [{"role": "user", "content": "private prompt"}],
        options=llm.LLMOptions("litellm", "model", None, secret, 10),
    )

    assert result is None
    assert secret not in str(warning.call_args)
    assert "private prompt" not in str(warning.call_args)
