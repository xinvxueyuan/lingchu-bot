"""Tests for the LLM chat nested subplugin handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from nonebot.exception import FinishedException

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.contracts import (
    SubpluginLLMError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.llm_chat import handler
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.llm_chat.config import (
    ChatConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.llm_chat.handler import (
    chat_cmd,
)


def _make_config(
    *, enabled: bool = True, system_prompt: str = "你是一个友好的群聊助手。"
) -> ChatConfig:
    """Create a ChatConfig with the given fields."""
    return ChatConfig(enabled=enabled, system_prompt=system_prompt)


def finish_text(mock_finish: MagicMock) -> str:
    """Return the message argument received by matcher.finish."""
    call_args = mock_finish.call_args
    if call_args is None:
        return ""
    if "message" in call_args.kwargs:
        return str(call_args.kwargs["message"])
    if call_args.args:
        return str(call_args.args[0])
    return ""


@pytest.fixture(autouse=True)
def mock_finish(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    finish = AsyncMock(side_effect=FinishedException)
    monkeypatch.setattr(chat_cmd, "finish", finish)
    return finish


async def test_chat_success(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
) -> None:
    """LLM returns text; finish receives the response."""
    config = _make_config()
    monkeypatch.setattr(handler, "get_chat_config", lambda: config)
    complete_subplugin_chat_default = AsyncMock(
        return_value="你好！有什么可以帮你的吗？"
    )
    monkeypatch.setattr(
        handler, "complete_subplugin_chat_default", complete_subplugin_chat_default
    )

    with pytest.raises(FinishedException):
        await handler.chat_handler(text=["你好"], bot=MagicMock(), event=MagicMock())

    complete_subplugin_chat_default.assert_awaited_once()
    assert finish_text(mock_finish) == "你好！有什么可以帮你的吗？"


async def test_chat_llm_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
) -> None:
    """complete_subplugin_chat_default raises SubpluginLLMError; finish receives localized error."""
    config = _make_config()
    monkeypatch.setattr(handler, "get_chat_config", lambda: config)
    monkeypatch.setattr(
        handler,
        "complete_subplugin_chat_default",
        AsyncMock(side_effect=SubpluginLLMError()),
    )

    with pytest.raises(FinishedException):
        await handler.chat_handler(text=["你好"], bot=MagicMock(), event=MagicMock())

    assert finish_text(mock_finish) == "LLM 服务暂时不可用，请稍后再试"


async def test_chat_disabled(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
) -> None:
    """config.enabled=False; finish receives disabled message, LLM not called."""
    config = _make_config(enabled=False)
    monkeypatch.setattr(handler, "get_chat_config", lambda: config)
    complete_subplugin_chat_default = AsyncMock()
    monkeypatch.setattr(
        handler, "complete_subplugin_chat_default", complete_subplugin_chat_default
    )

    with pytest.raises(FinishedException):
        await handler.chat_handler(text=["你好"], bot=MagicMock(), event=MagicMock())

    complete_subplugin_chat_default.assert_not_awaited()
    assert finish_text(mock_finish) == "该功能已禁用"


async def test_chat_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """system_prompt is prepended as a system message before the user message."""
    config = _make_config(system_prompt="你是一个毒舌助手")
    monkeypatch.setattr(handler, "get_chat_config", lambda: config)
    complete_subplugin_chat_default = AsyncMock(return_value="ok")
    monkeypatch.setattr(
        handler, "complete_subplugin_chat_default", complete_subplugin_chat_default
    )

    with pytest.raises(FinishedException):
        await handler.chat_handler(
            text=["你好", "世界"], bot=MagicMock(), event=MagicMock()
        )

    call_kwargs = complete_subplugin_chat_default.call_args
    messages = (
        call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs["messages"]
    )
    assert messages[0] == {"role": "system", "content": "你是一个毒舌助手"}
    assert messages[1] == {"role": "user", "content": "你好 世界"}
