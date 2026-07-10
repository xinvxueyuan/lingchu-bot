from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import contracts


async def test_complete_subplugin_chat_forwards_explicit_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete_chat = AsyncMock(return_value="result")
    monkeypatch.setattr(contracts, "complete_chat", complete_chat)
    options = contracts.LLMOptions(
        provider="litellm",
        model="child-model",
        base_url=None,
        api_key=None,
        timeout=8.0,
    )
    messages = [{"role": "user", "content": "describe"}]

    assert (
        await contracts.complete_subplugin_chat(messages, options=options) == "result"
    )
    complete_chat.assert_awaited_once_with(messages, options=options)
