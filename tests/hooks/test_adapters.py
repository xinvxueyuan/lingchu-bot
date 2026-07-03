from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks import adapters
from src.plugins.nonebot_plugin_lingchu_bot.hooks.adapters import (
    NormalizedMessageEvent,
    PlatformContext,
    _first_attr,
    _json_summary,
    _jsonable,
    _safe_call,
    _stringify,
    normalize_message_event,
    resolve_platform_context,
)


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


def test_resolve_platform_context_known_adapter() -> None:
    ctx = resolve_platform_context(make_bot())
    assert isinstance(ctx, PlatformContext)
    assert ctx.platform_id == "qq"
    assert ctx.adapter_id == "~onebot.v11"
    assert ctx.bot_id == "bot-1"
    assert ctx.protocol_id is None


def test_resolve_platform_context_unknown_adapter() -> None:
    assert resolve_platform_context(make_bot("Custom")) is None


def test_normalize_message_event_truncates_text(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(adapters, "runtime_config", enabled_config)
    event = make_event()
    event.get_plaintext.return_value = "hello world"

    normalized = normalize_message_event(make_bot(), event)

    assert isinstance(normalized, NormalizedMessageEvent)
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
    monkeypatch.setattr(adapters, "runtime_config", enabled_config)
    event = make_event(message_id=None)
    event.data = SimpleNamespace(peer_id="group-1", segments=[])

    normalized = normalize_message_event(make_bot(), event)

    assert isinstance(normalized, NormalizedMessageEvent)
    assert normalized.identity.message_id is None
    assert normalized.identity.conversation_id == "group-1"


def test_normalize_message_event_prefers_group_id_over_session_id(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(adapters, "runtime_config", enabled_config)
    event = make_event(group_id=868258211)
    event.get_session_id.return_value = "group_868258211_3128682634"

    normalized = normalize_message_event(make_bot(), event)

    assert isinstance(normalized, NormalizedMessageEvent)
    assert normalized.identity.conversation_id == "868258211"


def test_normalize_message_event_unknown_adapter() -> None:
    assert normalize_message_event(make_bot("Custom"), make_event()) is None


def test_stringify_and_first_attr_and_safe_call() -> None:
    obj = SimpleNamespace(a=1, b=None, c="x")
    assert _first_attr(obj, "a", "b") == 1
    assert _first_attr(obj, "b", "a") == 1
    assert _first_attr(obj, "missing") is None
    assert _stringify(123) == "123"
    assert _stringify(None) is None
    assert _safe_call(obj, "nonexistent") is None

    mock = MagicMock()
    mock.get_user_id.return_value = "u"
    assert _safe_call(mock, "get_user_id") == "u"


def test_jsonable_and_summary() -> None:
    assert _json_summary({"a": 1}) == '{"a": 1}'
    assert _jsonable(b"hi") == "hi"

    class FakeModel:
        def model_dump(self, **kwargs: Any) -> dict[str, Any]:
            return {"k": "v"}

    assert _jsonable(FakeModel()) == {"k": "v"}

    class BrokenModel:
        def model_dump(self, **kwargs: Any) -> dict[str, Any]:
            raise TypeError

    assert isinstance(_jsonable(BrokenModel()), str)
