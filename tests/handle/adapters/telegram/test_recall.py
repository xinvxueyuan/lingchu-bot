from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.telegram.exception import ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.recall import (
    telegram_recall_message,
)


@pytest.mark.asyncio
async def test_telegram_recall_deletes_replied_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = SimpleNamespace(delete_message=AsyncMock(return_value=True))
    event = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        reply_to_message=SimpleNamespace(message_id=55),
    )
    session = AsyncMock()
    session.add = MagicMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.recall.recall_message_cmd.finish",
        AsyncMock(),
    )

    await telegram_recall_message(session, bot=bot, event=event)

    bot.delete_message.assert_awaited_once_with(chat_id=-1001, message_id=55)


@pytest.mark.asyncio
async def test_telegram_recall_requires_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = SimpleNamespace(delete_message=AsyncMock(return_value=True))
    event = SimpleNamespace(chat=SimpleNamespace(id=-1001), reply_to_message=None)
    finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.recall.recall_message_cmd.finish",
        finish,
    )

    await telegram_recall_message(AsyncMock(), bot=bot, event=event)

    bot.delete_message.assert_not_awaited()
    finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_recall_reports_rejected_api_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = SimpleNamespace(delete_message=AsyncMock(side_effect=ActionFailed("denied")))
    event = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        reply_to_message=SimpleNamespace(message_id=55),
    )
    finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.recall.recall_message_cmd.finish",
        finish,
    )

    await telegram_recall_message(AsyncMock(), bot=bot, event=event)

    finish.assert_awaited_once()
