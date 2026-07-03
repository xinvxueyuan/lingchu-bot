from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.hooks import adapters
from src.plugins.nonebot_plugin_lingchu_bot.hooks.adapters import MessageIdentity
from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import (
    message_store as handler_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.services import message_store


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
    """Patch ``runtime_config`` in all modules that imported the name."""
    monkeypatch.setattr(handler_module, "runtime_config", enabled_config)
    monkeypatch.setattr(message_store, "runtime_config", enabled_config)
    monkeypatch.setattr(adapters, "runtime_config", enabled_config)
    return enabled_config


def install_fire_and_forget_spy(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[Any, str]]:
    """Patch ``fire_and_forget`` on the handler module to capture coroutines."""
    captured: list[tuple[Any, str]] = []

    def _spy(coro: Any, *, name: str = "fire_and_forget") -> MagicMock:
        captured.append((coro, name))
        return MagicMock()

    monkeypatch.setattr(handler_module, "fire_and_forget", _spy)
    return captured


async def test_message_store_preprocessor_records_event(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_event = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    state: dict[str, Any] = {}
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_preprocessor(make_bot(), make_event(), state)

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_event_received"
    await coro
    record_event.assert_awaited_once()
    assert isinstance(state[message_store.STATE_KEY], MessageIdentity)


async def test_message_store_preprocessor_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    record_event = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_preprocessor(make_bot(), make_event(), {})

    assert captured == []
    record_event.assert_not_awaited()


async def test_message_store_preprocessor_skips_unknown_adapter(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_event = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_preprocessor(
        make_bot("Custom"), make_event(), {}
    )

    assert captured == []
    record_event.assert_not_awaited()


async def test_message_store_preprocessor_records_meta_event(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_event = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    captured = install_fire_and_forget_spy(monkeypatch)
    event = make_event()
    event.get_type.return_value = "meta_event"
    event.get_event_name.return_value = "meta_event.heartbeat"

    await handler_module.message_store_preprocessor(make_bot(), event, {})

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_event_received"
    await coro
    record_event.assert_awaited_once()
    assert record_event.await_args is not None
    record_kwargs = record_event.await_args.kwargs
    assert record_kwargs["event_type"] == "meta_event.heartbeat"
    assert record_kwargs["event_category"] == "meta_event"


async def test_message_store_preprocessor_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_event = AsyncMock(side_effect=DatabaseError("boom"))
    monkeypatch.setattr(message_store.repository, "record_event_received", record_event)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_preprocessor(make_bot(), make_event(), {})

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_event_received"
    await coro
    record_event.assert_awaited_once()


async def test_run_postprocessor_updates_status(
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
        protocol_id=None,
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )
    matcher = MagicMock()
    matcher.block = False
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_run_postprocessor(
        matcher,
        None,
        make_bot(),
        make_event(),
        {message_store.STATE_KEY: identity},
    )

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_matcher_result"
    await coro
    record_result.assert_awaited_once()
    assert record_result.await_args is not None
    assert record_result.await_args.kwargs["process_status"] == "handled"


async def test_run_postprocessor_blocked_status(
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
        protocol_id=None,
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )
    matcher = MagicMock()
    matcher.block = True
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_run_postprocessor(
        matcher,
        None,
        make_bot(),
        make_event(),
        {message_store.STATE_KEY: identity},
    )

    await captured[0][0]
    assert record_result.await_args is not None
    assert record_result.await_args.kwargs["process_status"] == "handled:blocked"


async def test_run_postprocessor_failed_status(
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
        protocol_id=None,
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
    )
    matcher = MagicMock()
    matcher.block = False
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_run_postprocessor(
        matcher,
        ValueError("oops"),
        make_bot(),
        make_event(),
        {message_store.STATE_KEY: identity},
    )

    await captured[0][0]
    assert record_result.await_args is not None
    assert record_result.await_args.kwargs["process_status"] == "failed"


async def test_run_postprocessor_skips_when_no_identity(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_result = AsyncMock()
    monkeypatch.setattr(
        message_store.repository, "record_matcher_result", record_result
    )
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_run_postprocessor(
        MagicMock(),
        None,
        make_bot(),
        make_event(),
        {},
    )

    assert captured == []
    record_result.assert_not_awaited()


async def test_run_postprocessor_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    record_result = AsyncMock()
    monkeypatch.setattr(
        message_store.repository, "record_matcher_result", record_result
    )
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.message_store_run_postprocessor(
        MagicMock(),
        None,
        make_bot(),
        make_event(),
        {},
    )

    assert captured == []
    record_result.assert_not_awaited()


async def test_event_postprocessor_and_run_preprocessor_noop(
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    await handler_module.message_store_postprocessor(make_bot(), make_event(), {})
    await handler_module.message_store_run_preprocessor(
        MagicMock(), make_bot(), make_event(), {}
    )
