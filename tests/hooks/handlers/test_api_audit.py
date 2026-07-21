from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.hooks import adapters
from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import (
    api_audit as handler_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.services import message_store


def make_bot(adapter_name: str = "OneBot V11") -> MagicMock:
    bot = MagicMock()
    bot.self_id = "bot-1"
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = adapter_name
    return bot


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
    monkeypatch.setattr(handler_module, "plugin_config", enabled_config)
    monkeypatch.setattr(message_store, "plugin_config", enabled_config)
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
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


async def test_on_called_api_records_result(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.on_called_api(
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
    assert record_api.await_args is not None
    audit_event = record_api.await_args.args[1]
    assert audit_event.api_name == "send_message"
    assert audit_event.adapter_id == "~onebot.v11"
    assert audit_event.data_summary == "{'message': 'hello'}"
    assert audit_event.result_summary == "{'message_id': 'out-1'}"


async def test_on_called_api_skips_when_message_store_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.on_called_api(make_bot(), None, "send_message", {}, {})

    assert captured == []
    record_api.assert_not_awaited()


async def test_on_called_api_skips_when_api_calls_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_record_api_calls = False
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.on_called_api(make_bot(), None, "send_message", {}, {})

    assert captured == []
    record_api.assert_not_awaited()


async def test_on_called_api_skips_unknown_adapter(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock()
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.on_called_api(make_bot("Custom"), None, "send_message", {}, {})

    assert captured == []
    record_api.assert_not_awaited()


async def test_on_called_api_swallows_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    record_api = AsyncMock(side_effect=DatabaseError("boom"))
    monkeypatch.setattr(message_store.repository, "record_api_call", record_api)
    captured = install_fire_and_forget_spy(monkeypatch)

    await handler_module.on_called_api(make_bot(), None, "send_message", {}, {})

    assert len(captured) == 1
    coro, name = captured[0]
    assert name == "record_api_call"
    await coro
    record_api.assert_awaited_once()


async def test_on_calling_api_noop(
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    await handler_module.on_calling_api(make_bot(), "send_message", {})
