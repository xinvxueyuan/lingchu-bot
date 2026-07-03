from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import bot_connection


@pytest.fixture
def captured_fire_and_forget(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, str]]:
    captured: list[tuple[Any, str]] = []

    def _spy(coro: Any, *, name: str = "fire_and_forget") -> None:
        captured.append((coro, name))

    monkeypatch.setattr(bot_connection, "fire_and_forget", _spy)
    return captured


@pytest.mark.asyncio
async def test_on_bot_connect_records_lifecycle_and_sends_feedback(
    monkeypatch: pytest.MonkeyPatch,
    captured_fire_and_forget: list[tuple[Any, str]],
) -> None:
    record_bot_lifecycle = AsyncMock()
    send_pending_restart_feedback = AsyncMock()
    monkeypatch.setattr(bot_connection, "record_bot_lifecycle", record_bot_lifecycle)
    monkeypatch.setattr(
        bot_connection, "send_pending_restart_feedback", send_pending_restart_feedback
    )

    bot = MagicMock()
    await bot_connection.on_bot_connect(bot)

    assert [name for _, name in captured_fire_and_forget] == [
        "record_bot_lifecycle",
        "send_protocol_restart_feedback",
    ]

    lifecycle_coro = captured_fire_and_forget[0][0]
    feedback_coro = captured_fire_and_forget[1][0]
    await lifecycle_coro
    await feedback_coro

    record_bot_lifecycle.assert_awaited_once_with(bot, "bot_connected")
    send_pending_restart_feedback.assert_awaited_once_with(bot)


@pytest.mark.asyncio
async def test_on_bot_disconnect_records_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    captured_fire_and_forget: list[tuple[Any, str]],
) -> None:
    record_bot_lifecycle = AsyncMock()
    monkeypatch.setattr(bot_connection, "record_bot_lifecycle", record_bot_lifecycle)

    bot = MagicMock()
    await bot_connection.on_bot_disconnect(bot)

    assert [name for _, name in captured_fire_and_forget] == ["record_bot_lifecycle"]

    await captured_fire_and_forget[0][0]

    record_bot_lifecycle.assert_awaited_once_with(bot, "bot_disconnected")


def test_driver_hooks_are_registered() -> None:
    """Importing the module registers handlers on the NoneBot driver."""
    assert bot_connection.driver is not None
    assert callable(bot_connection.on_bot_connect)
    assert callable(bot_connection.on_bot_disconnect)
