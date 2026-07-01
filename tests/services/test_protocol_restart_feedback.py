from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services import protocol_restart_feedback

if TYPE_CHECKING:
    from collections.abc import Coroutine


@pytest.fixture(autouse=True)
def clear_feedback_state() -> None:
    protocol_restart_feedback.clear_pending_restart_feedback()


def test_register_pending_restart_feedback_dedupes_by_adapter_and_bot() -> None:
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
    )
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="789",
    )

    pending = protocol_restart_feedback.list_pending_restart_feedback()

    assert len(pending) == 1
    assert pending[0].conversation_id == "789"


@pytest.mark.asyncio
async def test_send_pending_restart_feedback_sends_group_message() -> None:
    bot = MagicMock()
    bot.self_id = "123"
    bot.adapter.get_name.return_value = "OneBot V11"
    bot.send_group_msg = AsyncMock()
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
    )

    sent = await protocol_restart_feedback.send_pending_restart_feedback(bot)

    assert sent is True
    bot.send_group_msg.assert_awaited_once_with(
        group_id=456,
        message="协议端已重启并重新连接",
    )
    assert protocol_restart_feedback.list_pending_restart_feedback() == ()


@pytest.mark.asyncio
async def test_send_pending_restart_feedback_ignores_other_bot() -> None:
    bot = MagicMock()
    bot.self_id = "999"
    bot.adapter.get_name.return_value = "OneBot V11"
    bot.send_group_msg = AsyncMock()
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
    )

    sent = await protocol_restart_feedback.send_pending_restart_feedback(bot)

    assert sent is False
    bot.send_group_msg.assert_not_called()
    assert len(protocol_restart_feedback.list_pending_restart_feedback()) == 1


@pytest.mark.asyncio
async def test_send_pending_restart_feedback_retains_pending_on_send_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = MagicMock()
    bot.self_id = "123"
    bot.adapter.get_name.return_value = "OneBot V11"
    bot.send_group_msg = AsyncMock(side_effect=RuntimeError("temporary failure"))
    logger_exception = MagicMock()
    monkeypatch.setattr(protocol_restart_feedback.logger, "exception", logger_exception)
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
    )

    sent = await protocol_restart_feedback.send_pending_restart_feedback(bot)

    assert sent is False
    bot.send_group_msg.assert_awaited_once_with(
        group_id=456,
        message="协议端已重启并重新连接",
    )
    pending = protocol_restart_feedback.list_pending_restart_feedback()
    assert len(pending) == 1
    assert pending[0].conversation_id == "456"
    logger_exception.assert_called_once_with("Failed to send protocol restart feedback")


@pytest.mark.asyncio
async def test_send_pending_restart_feedback_retains_pending_for_wrong_adapter() -> (
    None
):
    bot = MagicMock()
    bot.self_id = "123"
    bot.adapter.get_name.return_value = "Other"
    bot.send_group_msg = AsyncMock()
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
    )

    sent = await protocol_restart_feedback.send_pending_restart_feedback(bot)

    assert sent is False
    bot.send_group_msg.assert_not_called()
    assert len(protocol_restart_feedback.list_pending_restart_feedback()) == 1


@pytest.mark.asyncio
async def test_send_pending_restart_feedback_retains_unsupported_conversation_type() -> (
    None
):
    bot = MagicMock()
    bot.self_id = "123"
    bot.adapter.get_name.return_value = "OneBot V11"
    bot.send_group_msg = AsyncMock()
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="private",
        conversation_id="456",
    )

    sent = await protocol_restart_feedback.send_pending_restart_feedback(bot)

    assert sent is False
    bot.send_group_msg.assert_not_called()
    pending = protocol_restart_feedback.list_pending_restart_feedback()
    assert len(pending) == 1
    assert pending[0].conversation_type == "private"


def test_list_pending_restart_feedback_removes_expired_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 1000.0
    monkeypatch.setattr(protocol_restart_feedback, "monotonic", lambda: now)
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
    )
    monkeypatch.setattr(protocol_restart_feedback, "monotonic", lambda: now + 301.0)

    assert protocol_restart_feedback.list_pending_restart_feedback() == ()


@pytest.mark.asyncio
async def test_record_bot_connected_schedules_restart_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.start import startup as startup_module

    scheduled: list[tuple[str, Coroutine[Any, Any, Any]]] = []

    async def _record_bot_lifecycle(_bot: Any, _event_type: str) -> None:
        return None

    async def _send_pending_restart_feedback(_bot: Any) -> bool:
        return True

    def _fire_and_forget(
        coro: Coroutine[Any, Any, Any], *, name: str = "fire_and_forget"
    ) -> None:
        scheduled.append((name, coro))
        coro.close()

    monkeypatch.setattr(startup_module, "record_bot_lifecycle", _record_bot_lifecycle)
    monkeypatch.setattr(
        startup_module, "send_pending_restart_feedback", _send_pending_restart_feedback
    )
    monkeypatch.setattr(startup_module, "fire_and_forget", _fire_and_forget)

    await startup_module.record_bot_connected(MagicMock())

    assert [name for name, _ in scheduled] == [
        "record_bot_lifecycle",
        "send_protocol_restart_feedback",
    ]
