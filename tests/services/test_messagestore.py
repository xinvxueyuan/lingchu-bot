from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services import messagestore


def make_bot(adapter_name: str = "OneBot V11") -> MagicMock:
    bot = MagicMock()
    bot.self_id = "bot-1"
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = adapter_name
    return bot


def make_event(**overrides: Any) -> MagicMock:
    event = MagicMock()
    event.get_event_name.return_value = "message.group"
    event.get_type.return_value = "message"
    event.get_session_id.return_value = "group-1"
    event.get_user_id.return_value = "user-1"
    event.get_plaintext.return_value = "hello"
    event.get_message.return_value = "hello"
    event.message_id = "msg-1"
    event.id = None
    event.message_type = "group"
    event.data = SimpleNamespace(peer_id="group-1", segments=[])
    for key, value in overrides.items():
        setattr(event, key, value)
    return event


@pytest.fixture
def enabled_config() -> SimpleNamespace:
    return SimpleNamespace(
        message_store_enabled=True,
        message_store_retention_days=30,
        message_store_summary_limit=10,
        message_store_record_api_calls=True,
        message_store_cleanup_enabled=True,
    )


def install_fire_and_forget_spy(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[Any, str]]:
    """Patch ``fire_and_forget`` on the messagestore module to capture coroutines.

    Returns a list of ``(coroutine, name)`` tuples so tests can assert that
    background scheduling happened (and optionally await the coroutine to
    verify the repository call behaviour).
    """
    captured: list[tuple[Any, str]] = []

    def _spy(coro: Any, *, name: str = "fire_and_forget") -> Any:
        captured.append((coro, name))
        return MagicMock()

    monkeypatch.setattr(messagestore, "fire_and_forget", _spy)
    return captured


def test_normalize_message_event_truncates_text(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    event = make_event()
    event.get_plaintext.return_value = "hello world"

    normalized = messagestore.normalize_message_event(make_bot(), event)

    assert normalized is not None
    assert normalized.identity.platform_id == "qq"
    assert normalized.identity.adapter_id == "~onebot.v11"
    assert normalized.identity.protocol_id is None
    assert normalized.identity.bot_id == "bot-1"
    assert normalized.identity.conversation_id == "group-1"
    assert normalized.identity.message_id == "msg-1"
    assert normalized.user_id == "user-1"
    assert normalized.text_summary == "hello worl..."
    assert normalized.raw_message == '"hello"'
    assert '"peer_id": "group-1"' in (normalized.raw_event or "")


def test_normalize_message_event_handles_missing_message_id(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    event = make_event(message_id=None)
    event.data = SimpleNamespace(peer_id="group-1", segments=[])

    normalized = messagestore.normalize_message_event(make_bot(), event)

    assert normalized is not None
    assert normalized.identity.message_id is None
    assert normalized.identity.conversation_id == "group-1"


async def test_message_store_preprocessor_records_event(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_event = AsyncMock()
    monkeypatch.setattr(messagestore.repository, "record_event_received", record_event)
    state: dict[str, Any] = {}
    captured = install_fire_and_forget_spy(monkeypatch)

    await messagestore.message_store_preprocessor(make_bot(), make_event(), state)

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_event_received"
    await coro
    record_event.assert_awaited_once()
    assert isinstance(state[messagestore.STATE_KEY], messagestore.MessageIdentity)


async def test_message_store_preprocessor_skips_disabled_known_adapter(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_event = AsyncMock()
    monkeypatch.setattr(messagestore.repository, "record_event_received", record_event)
    state: dict[str, Any] = {}
    captured = install_fire_and_forget_spy(monkeypatch)

    await messagestore.message_store_preprocessor(
        make_bot("Milky"),
        make_event(),
        state,
    )

    assert captured == []
    assert messagestore.STATE_KEY not in state


async def test_message_store_preprocessor_skips_unknown_adapter(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_event = AsyncMock()
    monkeypatch.setattr(messagestore.repository, "record_event_received", record_event)
    captured = install_fire_and_forget_spy(monkeypatch)

    await messagestore.message_store_preprocessor(
        make_bot("Custom"),
        make_event(),
        {},
    )

    assert captured == []


async def test_message_store_preprocessor_skips_meta_event(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_event = AsyncMock()
    monkeypatch.setattr(messagestore.repository, "record_event_received", record_event)
    captured = install_fire_and_forget_spy(monkeypatch)
    event = make_event()
    event.get_type.return_value = "meta_event"
    event.get_event_name.return_value = "meta_event.heartbeat"

    await messagestore.message_store_preprocessor(make_bot(), event, {})

    assert captured == []


async def test_message_store_preprocessor_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_event = AsyncMock(side_effect=messagestore.DatabaseError("boom"))
    monkeypatch.setattr(messagestore.repository, "record_event_received", record_event)
    captured = install_fire_and_forget_spy(monkeypatch)

    await messagestore.message_store_preprocessor(make_bot(), make_event(), {})

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_event_received"
    await coro  # DatabaseError is swallowed inside the scheduled coroutine
    record_event.assert_awaited_once()


async def test_run_postprocessor_updates_status(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_result = AsyncMock()
    monkeypatch.setattr(messagestore.repository, "record_matcher_result", record_result)
    identity = messagestore.MessageIdentity(
        platform_id="qq",
        adapter_id="~milky",
        protocol_id=None,
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )
    matcher = MagicMock()
    matcher.block = False
    captured = install_fire_and_forget_spy(monkeypatch)

    await messagestore.message_store_run_postprocessor(
        matcher,
        None,
        {messagestore.STATE_KEY: identity},
    )

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_matcher_result"
    await coro
    record_result.assert_awaited_once()
    record_result_args = record_result.await_args
    assert record_result_args is not None
    assert record_result_args.kwargs["adapter_id"] == "~milky"
    assert record_result_args.kwargs["process_status"] == "handled"


async def test_on_called_api_records_result(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_api = AsyncMock()
    monkeypatch.setattr(messagestore.repository, "record_api_call", record_api)
    captured = install_fire_and_forget_spy(monkeypatch)

    await messagestore.message_store_on_called_api(
        make_bot(),
        None,
        "send_message",
        {"message": "hello"},
        {"message_id": "out-1"},
    )

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_api_call"
    await coro
    record_api.assert_awaited_once()
    record_api_args = record_api.await_args
    assert record_api_args is not None
    assert record_api_args.kwargs["api_name"] == "send_message"
    assert record_api_args.kwargs["adapter_id"] == "~onebot.v11"


async def test_lifecycle_and_api_recording_skip_disabled_known_adapter(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(messagestore, "runtime_config", enabled_config)
    record_api = AsyncMock()
    monkeypatch.setattr(messagestore.repository, "record_api_call", record_api)
    captured = install_fire_and_forget_spy(monkeypatch)

    lifecycle_recorded = await messagestore.record_bot_lifecycle(
        make_bot("Milky"),
        "bot_connected",
    )
    await messagestore.message_store_on_called_api(
        make_bot("Milky"),
        None,
        "send_message",
        {"message": "hello"},
        {"message_id": "out-1"},
    )

    assert not lifecycle_recorded
    assert captured == []
