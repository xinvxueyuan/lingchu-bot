from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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


def install_handle_api_called_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> MagicMock:
    """Patch ``handle_api_called`` on the handler module to capture calls."""
    mock = MagicMock()
    monkeypatch.setattr(handler_module, "handle_api_called", mock)
    return mock


async def test_on_called_api_records_result(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    handle_api_called = install_handle_api_called_mock(monkeypatch)

    await handler_module.on_called_api(
        make_bot(),
        None,
        "send_message",
        {"message": "hello"},
        {"message_id": "out-1"},
    )

    handle_api_called.assert_called_once()
    args = handle_api_called.call_args.args
    assert args[2] == "send_message"
    assert args[3] == {"message": "hello"}
    assert args[4] == {"message_id": "out-1"}
    assert args[0].adapter_id == "~onebot.v11"


async def test_on_called_api_skips_when_message_store_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_enabled = False
    handle_api_called = install_handle_api_called_mock(monkeypatch)

    await handler_module.on_called_api(make_bot(), None, "send_message", {}, {})

    handle_api_called.assert_not_called()


async def test_on_called_api_skips_when_api_calls_disabled(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    patched_runtime_config.message_store_record_api_calls = False
    handle_api_called = install_handle_api_called_mock(monkeypatch)

    await handler_module.on_called_api(make_bot(), None, "send_message", {}, {})

    handle_api_called.assert_not_called()


async def test_on_called_api_skips_unknown_adapter(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    handle_api_called = install_handle_api_called_mock(monkeypatch)

    await handler_module.on_called_api(make_bot("Custom"), None, "send_message", {}, {})

    handle_api_called.assert_not_called()


async def test_on_calling_api_noop(
    patched_runtime_config: SimpleNamespace,
) -> None:
    _ = patched_runtime_config
    await handler_module.on_calling_api(make_bot(), "send_message", {})


async def test_on_called_api_swallows_context_resolution_errors(
    monkeypatch: pytest.MonkeyPatch,
    patched_runtime_config: SimpleNamespace,
) -> None:
    """resolve_platform_context 意外异常时不冒泡到适配器 API 调用路径。"""
    _ = patched_runtime_config
    handle_api_called = install_handle_api_called_mock(monkeypatch)
    monkeypatch.setattr(
        handler_module,
        "resolve_platform_context",
        MagicMock(side_effect=RuntimeError("boom")),
    )

    await handler_module.on_called_api(make_bot(), None, "send_message", {}, {})

    handle_api_called.assert_not_called()
