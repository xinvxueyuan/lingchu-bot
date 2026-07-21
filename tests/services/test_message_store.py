from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.hooks import adapters
from src.plugins.nonebot_plugin_lingchu_bot.hooks.adapters import MessageIdentity
from src.plugins.nonebot_plugin_lingchu_bot.services import message_store


class _FakeSessionContext:
    """Async context manager that yields a fixed mock session."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def __aenter__(self) -> Any:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


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
    event.group_id = "group-1"
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


@pytest.fixture
def patched_runtime_config(
    monkeypatch: pytest.MonkeyPatch, enabled_config: SimpleNamespace
):
    """Patch ``plugin_config`` in all modules that imported the name."""
    monkeypatch.setattr(message_store, "plugin_config", enabled_config)
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
    return enabled_config


@pytest.fixture(autouse=True)
def patched_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch ``get_session`` in ``message_store`` to yield a mock session."""
    session = MagicMock(name="async_session")
    monkeypatch.setattr(
        message_store,
        "get_session",
        lambda: _FakeSessionContext(session),
    )
    return session


async def test_handle_event_received_records_event(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_event = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    normalized = adapters.normalize_message_event(make_bot(), make_event())
    assert normalized is not None

    await message_store.handle_event_received(normalized)

    record_event.assert_awaited_once()
    assert record_event.await_args is not None
    record_kwargs = record_event.await_args.kwargs
    assert record_kwargs["platform_id"] == "qq"
    assert record_kwargs["adapter_id"] == "~onebot.v11"
    assert record_kwargs["protocol_id"] == "default"
    assert record_kwargs["bot_id"] == "bot-1"
    assert record_kwargs["conversation_id"] == "group-1"
    assert record_kwargs["message_id"] == "msg-1"
    assert record_kwargs["event_type"] == "message.group"
    assert record_kwargs["event_category"] == "message"


async def test_handle_event_received_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    record_event = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    normalized = adapters.normalize_message_event(make_bot(), make_event())
    assert normalized is not None

    await message_store.handle_event_received(normalized)

    record_event.assert_not_awaited()


async def test_handle_event_received_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_event = AsyncMock(side_effect=DatabaseError("boom"))
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    normalized = adapters.normalize_message_event(make_bot(), make_event())
    assert normalized is not None

    await message_store.handle_event_received(normalized)

    record_event.assert_awaited_once()


async def test_handle_matcher_result_records_handled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_result = AsyncMock(return_value=True)
    monkeypatch.setattr(
        message_store.repository, "record_matcher_result", record_result
    )
    identity = MessageIdentity(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="default",
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )
    matcher = MagicMock()
    matcher.block = False

    result = await message_store.handle_matcher_result(identity, matcher, None)

    assert result is True
    record_result.assert_awaited_once()
    assert record_result.await_args is not None
    record_kwargs = record_result.await_args.kwargs
    assert record_kwargs["process_status"] == "handled"
    assert record_kwargs["adapter_id"] == "~onebot.v11"


async def test_handle_matcher_result_records_blocked_and_failed(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_result = AsyncMock(return_value=True)
    monkeypatch.setattr(
        message_store.repository, "record_matcher_result", record_result
    )
    identity = MessageIdentity(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="default",
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )
    matcher = MagicMock()
    matcher.block = True

    await message_store.handle_matcher_result(identity, matcher, ValueError("oops"))

    assert record_result.await_args is not None
    assert record_result.await_args.kwargs["process_status"] == "failed:blocked"


async def test_handle_matcher_result_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    record_result = AsyncMock()
    monkeypatch.setattr(
        message_store.repository, "record_matcher_result", record_result
    )
    identity = MessageIdentity(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="default",
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )

    result = await message_store.handle_matcher_result(identity, MagicMock(), None)

    assert result is False
    record_result.assert_not_awaited()


async def test_handle_matcher_result_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_result = AsyncMock(side_effect=DatabaseError("boom"))
    monkeypatch.setattr(
        message_store.repository, "record_matcher_result", record_result
    )
    identity = MessageIdentity(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="default",
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )

    result = await message_store.handle_matcher_result(identity, MagicMock(), None)

    assert result is False
    record_result.assert_awaited_once()


async def test_handle_api_called_records_result(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
    patched_session: MagicMock,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    platform_context = adapters.resolve_platform_context(make_bot())
    assert platform_context is not None

    await message_store.handle_api_called(
        platform_context,
        None,
        "send_message",
        {"message": "hello"},
        {"message_id": "out-1"},
    )

    record_api.assert_awaited_once()
    assert record_api.await_args is not None
    assert record_api.await_args.args[0] is patched_session
    audit_event = record_api.await_args.args[1]
    assert audit_event.api_name == "send_message"
    assert audit_event.adapter_id == "~onebot.v11"
    assert audit_event.data_summary == "{'message': 'hello'}"
    assert audit_event.result_summary == "{'message_id': 'out-1'}"


async def test_handle_api_called_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    platform_context = adapters.resolve_platform_context(make_bot())
    assert platform_context is not None

    await message_store.handle_api_called(
        platform_context,
        None,
        "send_message",
        {},
        {},
    )

    record_api.assert_not_awaited()


async def test_handle_api_called_skips_when_api_calls_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_record_api_calls = False
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    platform_context = adapters.resolve_platform_context(make_bot())
    assert platform_context is not None

    await message_store.handle_api_called(
        platform_context,
        None,
        "send_message",
        {},
        {},
    )

    record_api.assert_not_awaited()


async def test_handle_api_called_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock(side_effect=DatabaseError("boom"))
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    platform_context = adapters.resolve_platform_context(make_bot())
    assert platform_context is not None

    await message_store.handle_api_called(
        platform_context,
        None,
        "send_message",
        {},
        {},
    )

    record_api.assert_awaited_once()


async def test_record_bot_lifecycle_records_connected(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
    patched_session: MagicMock,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)

    result = await message_store.record_bot_lifecycle(make_bot(), "bot_connected")

    assert result is True
    record_api.assert_awaited_once()
    assert record_api.await_args is not None
    assert record_api.await_args.args[0] is patched_session
    audit_event = record_api.await_args.args[1]
    assert audit_event.api_name == "bot_connected"
    assert audit_event.audit_type == "lifecycle"
    assert audit_event.adapter_id == "~onebot.v11"


async def test_record_bot_lifecycle_skips_unknown_adapter(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)

    result = await message_store.record_bot_lifecycle(
        make_bot("Custom"), "bot_connected"
    )

    assert result is False
    record_api.assert_not_awaited()


async def test_record_bot_lifecycle_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)

    result = await message_store.record_bot_lifecycle(make_bot(), "bot_connected")

    assert result is False
    record_api.assert_not_awaited()


async def test_record_bot_lifecycle_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock(side_effect=DatabaseError("boom"))
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)

    result = await message_store.record_bot_lifecycle(make_bot(), "bot_connected")

    assert result is False
    record_api.assert_awaited_once()


def test_truncate_returns_none_for_none_value() -> None:
    assert message_store._truncate(None) is None


def test_truncate_returns_value_unchanged_when_within_limit() -> None:
    assert message_store._truncate("hello", 10) == "hello"


def test_truncate_returns_value_unchanged_when_size_le_zero() -> None:
    assert message_store._truncate("hello", 0) == "hello"
    assert message_store._truncate("hello", -1) == "hello"


def test_truncate_truncates_long_value_with_ellipsis() -> None:
    assert message_store._truncate("hello world", 5) == "hello..."


def test_truncate_uses_runtime_config_limit_when_no_limit_passed(
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    assert patched_runtime_config.message_store_summary_limit == 10
    assert message_store._truncate("0123456789ABC") == "0123456789..."


def test_stringify_returns_none_for_none_value() -> None:
    assert message_store._stringify(None) is None


def test_stringify_truncates_string_representation_of_arbitrary_value() -> None:
    assert message_store._stringify("hello world", limit=5) == "hello..."
    assert message_store._stringify(12345, limit=10) == "12345"


async def test_initialize_message_store_logs_disabled_when_disabled(
    patched_runtime_config: SimpleNamespace,
) -> None:
    patched_runtime_config.message_store_enabled = False
    await message_store.initialize_message_store()


async def test_initialize_message_store_logs_initialized_when_enabled(
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    await message_store.initialize_message_store()


async def test_shutdown_message_store_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    patched_runtime_config.message_store_enabled = False
    cleanup_mock = AsyncMock(return_value=(0, True))
    monkeypatch.setattr(message_store, "cleanup_expired_messages", cleanup_mock)

    await message_store.shutdown_message_store()

    cleanup_mock.assert_not_awaited()


async def test_shutdown_message_store_runs_cleanup_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    cleanup_mock = AsyncMock(return_value=(0, True))
    monkeypatch.setattr(message_store, "cleanup_expired_messages", cleanup_mock)

    await message_store.shutdown_message_store()

    cleanup_mock.assert_awaited_once()


async def test_cleanup_expired_messages_skips_when_store_disabled(
    patched_runtime_config: SimpleNamespace,
) -> None:
    patched_runtime_config.message_store_enabled = False
    result = await message_store.cleanup_expired_messages()
    assert result == (0, True)


async def test_cleanup_expired_messages_skips_when_cleanup_disabled(
    patched_runtime_config: SimpleNamespace,
) -> None:
    patched_runtime_config.message_store_cleanup_enabled = False
    result = await message_store.cleanup_expired_messages()
    assert result == (0, True)


async def test_cleanup_expired_messages_returns_count_when_successful(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
    patched_session: MagicMock,
) -> None:
    _ = patched_runtime_config
    cleanup_mock = AsyncMock(return_value=(7, True))
    monkeypatch.setattr(
        message_store.repository, "cleanup_expired_messages", cleanup_mock
    )

    result = await message_store.cleanup_expired_messages()

    assert result == (7, True)
    cleanup_mock.assert_awaited_once_with(
        patched_session,
        retention_days=30,
    )


async def test_cleanup_expired_messages_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    cleanup_mock = AsyncMock(side_effect=DatabaseError("boom"))
    monkeypatch.setattr(
        message_store.repository, "cleanup_expired_messages", cleanup_mock
    )

    result = await message_store.cleanup_expired_messages()

    assert result == (0, False)
    cleanup_mock.assert_awaited_once()


async def test_record_bot_lifecycle_handles_missing_adapter_attribute(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)

    bot = MagicMock()
    bot.self_id = "bot-1"
    bot.adapter = None

    result = await message_store.record_bot_lifecycle(bot, "bot_connected")

    assert result is False
    record_api.assert_not_awaited()


async def test_record_bot_lifecycle_falls_back_when_get_name_raises(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)

    bot = MagicMock()
    bot.self_id = "bot-1"
    bot.adapter = MagicMock()
    bot.adapter.get_name.side_effect = AttributeError("no name")

    result = await message_store.record_bot_lifecycle(bot, "bot_connected")

    assert result is False
    record_api.assert_not_awaited()


async def test_record_bot_lifecycle_skips_when_no_platform_profile(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    monkeypatch.setattr(message_store, "get_platform_profile", lambda _adapter_id: None)

    result = await message_store.record_bot_lifecycle(make_bot(), "bot_connected")

    assert result is False
    record_api.assert_not_awaited()
