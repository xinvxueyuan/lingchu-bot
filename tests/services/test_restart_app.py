from __future__ import annotations

import asyncio
from collections.abc import Iterator
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.onebot.v11 import Message as OneBot11Message
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
    PrivateMessageEvent as OneBot11PrivateMessageEvent,
    Sender as OneBot11Sender,
)
from nonebot.adapters.telegram.event import (
    GroupMessageEvent as TelegramGroupMessageEvent,
    PrivateMessageEvent as TelegramPrivateMessageEvent,
)
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services import restart_app


@pytest.fixture(autouse=True)
def clear_pending_restart_app_state() -> Iterator[None]:
    restart_app.clear_pending_restart_app()
    yield
    restart_app.clear_pending_restart_app()


def _register_pending() -> None:
    restart_app.register_pending_restart_app(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
        account_id="789",
    )


def _make_pending() -> restart_app.PendingRestartApp:
    return restart_app.PendingRestartApp(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="group",
        conversation_id="456",
        account_id="789",
        created_at=0.0,
    )


@pytest.mark.asyncio
async def test_register_pending_restart_app_is_listed_with_fields() -> None:
    _register_pending()

    pending = restart_app.list_pending_restart_app()

    assert len(pending) == 1
    item = pending[0]
    assert item.platform_id == "qq"
    assert item.adapter_id == "~onebot.v11"
    assert item.bot_id == "123"
    assert item.conversation_type == "group"
    assert item.conversation_id == "456"
    assert item.account_id == "789"
    assert item.created_at > 0.0


@pytest.mark.asyncio
async def test_clear_pending_restart_app_for_pops_once_then_returns_false() -> None:
    _register_pending()

    assert (
        restart_app.clear_pending_restart_app_for(
            platform_id="qq", conversation_id="456", account_id="789"
        )
        is True
    )
    assert restart_app.list_pending_restart_app() == ()
    assert (
        restart_app.clear_pending_restart_app_for(
            platform_id="qq", conversation_id="456", account_id="789"
        )
        is False
    )


@pytest.mark.asyncio
async def test_clear_pending_restart_app_clears_all() -> None:
    _register_pending()
    restart_app.register_pending_restart_app(
        platform_id="telegram",
        adapter_id="~telegram",
        bot_id="456",
        conversation_type="private",
        conversation_id="111",
        account_id="222",
    )

    restart_app.clear_pending_restart_app()

    assert restart_app.list_pending_restart_app() == ()


@pytest.mark.asyncio
async def test_ttl_timeout_clears_pending_and_notifies_conversation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(restart_app, "RESTART_CONFIRM_TTL_SECONDS", 0.01)
    fake_bot = MagicMock()
    monkeypatch.setattr(restart_app, "_get_bot", lambda _bot_id: fake_bot)
    send_to_conversation = AsyncMock()
    monkeypatch.setattr(restart_app, "_send_to_conversation", send_to_conversation)
    _register_pending()

    for _ in range(200):
        if (
            not restart_app.list_pending_restart_app()
            and send_to_conversation.await_count == 1
        ):
            break
        await asyncio.sleep(0.01)

    assert restart_app.list_pending_restart_app() == ()
    send_to_conversation.assert_awaited_once()
    call_args = send_to_conversation.await_args
    assert call_args is not None
    assert call_args.args[0] is fake_bot
    assert call_args.args[1].account_id == "789"
    assert call_args.args[2] == "重启已超时取消"


@pytest.mark.asyncio
async def test_execute_restart_app_writes_hosted_flag_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    flag_path = tmp_path / "restart.flag"
    monkeypatch.setenv(restart_app.LC_HOSTED_ENV, "1")
    monkeypatch.setenv(restart_app.RESTART_FLAG_PATH_ENV, str(flag_path))

    await restart_app.execute_restart_app(_make_pending())

    assert flag_path.read_text(encoding="utf-8") == json.dumps(
        {"platform": "qq", "account_id": "789"}, ensure_ascii=False
    )


@pytest.mark.asyncio
async def test_execute_restart_app_spawns_script_when_not_hosted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(restart_app.LC_HOSTED_ENV, raising=False)
    spawn_script = AsyncMock()
    monkeypatch.setattr(restart_app, "_spawn_restart_script", spawn_script)
    pending = _make_pending()

    await restart_app.execute_restart_app(pending)

    spawn_script.assert_awaited_once_with(pending)


@pytest.mark.asyncio
async def test_notify_restart_success_sends_private_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "OneBot V11"
    bot.send_private_msg = AsyncMock()
    monkeypatch.setattr(restart_app, "get_bots", lambda: {"bot1": bot})

    result = await restart_app.notify_restart_success("qq", "12345")

    assert result is True
    bot.send_private_msg.assert_awaited_once_with(
        user_id=12345, message="灵初已成功重启"
    )


@pytest.mark.asyncio
async def test_notify_restart_success_returns_false_without_matching_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "Other"
    bot.send_private_msg = AsyncMock()
    monkeypatch.setattr(restart_app, "get_bots", lambda: {"bot1": bot})

    result = await restart_app.notify_restart_success("qq", "12345")

    assert result is False
    bot.send_private_msg.assert_not_called()


@pytest.mark.asyncio
async def test_handle_restart_app_confirm_confirms_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        restart_app,
        "_extract_context",
        lambda _bot, _event: ("qq", "group", "456", "789"),
    )
    matcher_send = AsyncMock()
    monkeypatch.setattr(restart_app._restart_app_confirm_matcher, "send", matcher_send)
    execute_restart = AsyncMock()
    monkeypatch.setattr(restart_app, "execute_restart_app", execute_restart)
    _register_pending()
    event = MagicMock()
    event.get_plaintext.return_value = "是"

    await restart_app._handle_restart_app_confirm(MagicMock(), event)

    execute_restart.assert_awaited_once()
    executed = execute_restart.await_args
    assert executed is not None
    assert executed.args[0].account_id == "789"
    assert restart_app.list_pending_restart_app() == ()
    matcher_send.assert_awaited_once_with("正在重启应用，请稍候...")


@pytest.mark.asyncio
async def test_handle_restart_app_confirm_cancels_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        restart_app,
        "_extract_context",
        lambda _bot, _event: ("qq", "group", "456", "789"),
    )
    matcher_send = AsyncMock()
    monkeypatch.setattr(restart_app._restart_app_confirm_matcher, "send", matcher_send)
    execute_restart = AsyncMock()
    monkeypatch.setattr(restart_app, "execute_restart_app", execute_restart)
    _register_pending()
    event = MagicMock()
    event.get_plaintext.return_value = "取消"

    await restart_app._handle_restart_app_confirm(MagicMock(), event)

    execute_restart.assert_not_awaited()
    assert restart_app.list_pending_restart_app() == ()
    matcher_send.assert_awaited_once_with("已取消重启")


@pytest.mark.asyncio
async def test_handle_restart_app_confirm_ignores_unrelated_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        restart_app,
        "_extract_context",
        lambda _bot, _event: ("qq", "group", "456", "789"),
    )
    matcher_send = AsyncMock()
    monkeypatch.setattr(restart_app._restart_app_confirm_matcher, "send", matcher_send)
    execute_restart = AsyncMock()
    monkeypatch.setattr(restart_app, "execute_restart_app", execute_restart)
    _register_pending()
    event = MagicMock()
    event.get_plaintext.return_value = "随便聊聊"

    await restart_app._handle_restart_app_confirm(MagicMock(), event)

    execute_restart.assert_not_awaited()
    matcher_send.assert_not_awaited()
    pending = restart_app.list_pending_restart_app()
    assert len(pending) == 1
    assert pending[0].account_id == "789"


def _make_pending_private() -> restart_app.PendingRestartApp:
    return restart_app.PendingRestartApp(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="123",
        conversation_type="private",
        conversation_id="456",
        account_id="789",
        created_at=0.0,
    )


def _make_telegram_pending(
    *, conversation_type: str = "private"
) -> restart_app.PendingRestartApp:
    return restart_app.PendingRestartApp(
        platform_id="telegram",
        adapter_id="~telegram",
        bot_id="456",
        conversation_type=conversation_type,
        conversation_id="111",
        account_id="222",
        created_at=0.0,
    )


def _make_onebot11_private_event(user_id: int = 789) -> OneBot11PrivateMessageEvent:
    return OneBot11PrivateMessageEvent(
        time=0,
        self_id=100,
        post_type="message",
        sub_type="friend",
        user_id=user_id,
        message_type="private",
        message_id=1,
        message=OneBot11Message("hi"),
        original_message=OneBot11Message("hi"),
        raw_message="hi",
        font=0,
        sender=OneBot11Sender(user_id=user_id),
    )


def _make_onebot11_group_event(
    user_id: int = 789, group_id: int = 456
) -> OneBot11GroupMessageEvent:
    return OneBot11GroupMessageEvent(
        time=0,
        self_id=100,
        post_type="message",
        sub_type="group",
        user_id=user_id,
        message_type="group",
        message_id=1,
        message=OneBot11Message("hi"),
        original_message=OneBot11Message("hi"),
        raw_message="hi",
        font=0,
        sender=OneBot11Sender(user_id=user_id),
        group_id=group_id,
    )


def _make_telegram_private_event(
    user_id: int = 222, chat_id: int = 111
) -> TelegramPrivateMessageEvent:
    return TelegramPrivateMessageEvent.model_validate({
        "message_id": 1,
        "date": 0,
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": user_id, "is_bot": False, "first_name": "tester"},
        "message": "hi",
    })


def _make_telegram_group_event(
    user_id: int = 222, chat_id: int = 111
) -> TelegramGroupMessageEvent:
    return TelegramGroupMessageEvent.model_validate({
        "message_id": 1,
        "date": 0,
        "chat": {"id": chat_id, "type": "group"},
        "from": {"id": user_id, "is_bot": False, "first_name": "tester"},
        "message": "hi",
    })


def test_extract_context_onebot11_private() -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "OneBot V11"

    context = restart_app._extract_context(bot, _make_onebot11_private_event())

    assert context == ("qq", "private", "789", "789")


def test_extract_context_onebot11_group() -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "OneBot V11"

    context = restart_app._extract_context(bot, _make_onebot11_group_event())

    assert context == ("qq", "group", "456", "789")


def test_extract_context_telegram_private(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "Telegram"
    monkeypatch.setattr(
        restart_app,
        "get_platform_profile",
        lambda _adapter_id: SimpleNamespace(platform_id="telegram"),
    )

    context = restart_app._extract_context(bot, _make_telegram_private_event())

    assert context == ("telegram", "private", "111", "222")


def test_extract_context_telegram_group(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "Telegram"
    monkeypatch.setattr(
        restart_app,
        "get_platform_profile",
        lambda _adapter_id: SimpleNamespace(platform_id="telegram"),
    )

    context = restart_app._extract_context(bot, _make_telegram_group_event())

    assert context == ("telegram", "group", "111", "222")


def test_extract_context_unknown_adapter_returns_none() -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "Other"

    assert restart_app._extract_context(bot, MagicMock()) is None


def test_extract_context_adapter_without_get_name_returns_none() -> None:
    bot = MagicMock()
    bot.adapter = object()

    assert restart_app._extract_context(bot, MagicMock()) is None


@pytest.mark.asyncio
async def test_send_to_conversation_qq_private() -> None:
    bot = MagicMock()
    bot.send_private_msg = AsyncMock()

    await restart_app._send_to_conversation(bot, _make_pending_private(), "msg")

    bot.send_private_msg.assert_awaited_once_with(user_id=789, message="msg")


@pytest.mark.asyncio
async def test_send_to_conversation_qq_group() -> None:
    bot = MagicMock()
    bot.send_group_msg = AsyncMock()

    await restart_app._send_to_conversation(bot, _make_pending(), "msg")

    bot.send_group_msg.assert_awaited_once_with(group_id=456, message="msg")


@pytest.mark.asyncio
async def test_send_to_conversation_telegram_private() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await restart_app._send_to_conversation(bot, _make_telegram_pending(), "msg")

    bot.send_message.assert_awaited_once_with(chat_id=222, text="msg")


@pytest.mark.asyncio
async def test_send_to_conversation_telegram_group() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()

    await restart_app._send_to_conversation(
        bot, _make_telegram_pending(conversation_type="group"), "msg"
    )

    bot.send_message.assert_awaited_once_with(chat_id=111, text="msg")


@pytest.mark.asyncio
async def test_send_to_conversation_none_bot_returns() -> None:
    await restart_app._send_to_conversation(None, _make_pending(), "msg")


@pytest.mark.asyncio
async def test_write_restart_flag_missing_env_logs_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(restart_app.RESTART_FLAG_PATH_ENV, raising=False)
    logger_error = MagicMock()
    monkeypatch.setattr(restart_app.logger, "error", logger_error)

    await restart_app._write_restart_flag(_make_pending())

    logger_error.assert_called_once_with(
        "{} is not set; cannot request a hosted restart",
        restart_app.RESTART_FLAG_PATH_ENV,
    )


@pytest.mark.asyncio
async def test_write_restart_flag_writes_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    flag_path = tmp_path / "restart.flag"
    monkeypatch.setenv(restart_app.RESTART_FLAG_PATH_ENV, str(flag_path))

    await restart_app._write_restart_flag(_make_pending())

    assert flag_path.read_text(encoding="utf-8") == json.dumps(
        {"platform": "qq", "account_id": "789"}, ensure_ascii=False
    )


@pytest.mark.asyncio
async def test_spawn_restart_script_copy_failure_logs_and_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        restart_app.shutil, "copy2", MagicMock(side_effect=OSError("copy failed"))
    )
    logger_exception = MagicMock()
    monkeypatch.setattr(restart_app.logger, "exception", logger_exception)

    await restart_app._spawn_restart_script(_make_pending())

    logger_exception.assert_called_once_with("Failed to copy restart worker script")


@pytest.mark.asyncio
async def test_spawn_restart_script_subprocess_failure_logs_and_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(restart_app.shutil, "copy2", MagicMock())
    monkeypatch.setattr(
        restart_app.asyncio,
        "create_subprocess_exec",
        AsyncMock(side_effect=OSError("spawn failed")),
    )
    logger_exception = MagicMock()
    monkeypatch.setattr(restart_app.logger, "exception", logger_exception)

    await restart_app._spawn_restart_script(_make_pending())

    logger_exception.assert_called_once_with("Failed to spawn restart worker script")


@pytest.mark.asyncio
async def test_spawn_restart_script_success_tracks_proc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(restart_app.shutil, "copy2", MagicMock())
    proc = MagicMock()
    monkeypatch.setattr(
        restart_app.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=proc),
    )

    await restart_app._spawn_restart_script(_make_pending())

    assert proc in restart_app._spawned_scripts


def test_get_bot_returns_none_on_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_bot_id: str) -> None:
        raise ValueError("bot not found")

    monkeypatch.setattr(restart_app, "get_bot", _raise)

    assert restart_app._get_bot("123") is None


def test_get_bot_returns_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = MagicMock()
    monkeypatch.setattr(restart_app, "get_bot", lambda _bot_id: bot)

    assert restart_app._get_bot("123") is bot


@pytest.mark.asyncio
async def test_notify_restart_success_telegram_sends_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "Telegram"
    bot.send_message = AsyncMock()
    monkeypatch.setattr(restart_app, "get_bots", lambda: {"bot1": bot})
    monkeypatch.setattr(
        restart_app,
        "get_platform_profile",
        lambda _adapter_id: SimpleNamespace(platform_id="telegram"),
    )

    result = await restart_app.notify_restart_success("telegram", "222")

    assert result is True
    bot.send_message.assert_awaited_once_with(chat_id=222, text="灵初已成功重启")


@pytest.mark.asyncio
async def test_notify_restart_success_continues_after_send_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot1 = MagicMock()
    bot1.adapter.get_name.return_value = "OneBot V11"
    bot1.send_private_msg = AsyncMock(side_effect=RuntimeError("send failed"))
    bot2 = MagicMock()
    bot2.adapter.get_name.return_value = "OneBot V11"
    bot2.send_private_msg = AsyncMock(side_effect=RuntimeError("send failed"))
    monkeypatch.setattr(restart_app, "get_bots", lambda: {"bot1": bot1, "bot2": bot2})
    logger_exception = MagicMock()
    monkeypatch.setattr(restart_app.logger, "exception", logger_exception)

    result = await restart_app.notify_restart_success("qq", "12345")

    assert result is False
    bot1.send_private_msg.assert_awaited_once()
    bot2.send_private_msg.assert_awaited_once()
    assert logger_exception.call_count == 2


def test_extract_bot_platform_get_name_raises_returns_none() -> None:
    bot = MagicMock()
    bot.adapter.get_name.side_effect = ValueError("boom")

    assert restart_app._extract_bot_platform(bot) is None


def test_extract_bot_platform_unknown_adapter_returns_none() -> None:
    bot = MagicMock()
    bot.adapter.get_name.return_value = "Other"

    assert restart_app._extract_bot_platform(bot) is None


def test_extract_bot_platform_without_get_name_returns_none() -> None:
    bot = MagicMock()
    bot.adapter = object()

    assert restart_app._extract_bot_platform(bot) is None
