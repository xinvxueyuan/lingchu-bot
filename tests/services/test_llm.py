from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

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
