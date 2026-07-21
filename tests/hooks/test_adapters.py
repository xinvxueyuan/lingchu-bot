from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks import adapters
from src.plugins.nonebot_plugin_lingchu_bot.hooks.adapters import (
    NormalizedMessageEvent,
    PlatformContext,
    _adapter_identity,
    _adapter_name,
    _conversation_id,
    _first_attr,
    _json_summary,
    _jsonable,
    _message_type,
    _plain_text,
    _raw_message,
    _safe_call,
    _stringify,
    _truncate,
    _user_id,
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
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
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
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
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
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
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


def test_truncate_returns_none_for_none() -> None:
    assert _truncate(None) is None


def test_truncate_respects_explicit_limit() -> None:
    assert _truncate("hello world", limit=5) == "hello..."


def test_safe_call_swallows_exceptions() -> None:
    obj = MagicMock()
    obj.bad_method.side_effect = ValueError("bad")
    assert _safe_call(obj, "bad_method") is None


def test_adapter_name_returns_unknown_when_get_name_missing() -> None:
    bot = MagicMock()
    bot.adapter = SimpleNamespace()
    assert _adapter_name(bot) == "unknown"


def test_adapter_name_returns_unknown_when_get_name_raises() -> None:
    bot = MagicMock()
    bot.adapter.get_name.side_effect = TypeError("bad")
    assert _adapter_name(bot) == "unknown"


def test_adapter_identity_returns_none_when_profile_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapters, "resolve_adapter_id", MagicMock(return_value="~fake"))
    monkeypatch.setattr(adapters, "get_platform_profile", MagicMock(return_value=None))
    assert _adapter_identity("fake") is None


def test_message_type_falls_back_to_event_data() -> None:
    event = make_event(message_type=None)
    event.post_type = None
    event.data = SimpleNamespace(message_type="group", post_type=None)
    assert _message_type(event) == "group"


def test_conversation_id_falls_back_to_event_data() -> None:
    event = make_event(group_id=None)
    event.guild_id = None
    event.channel_id = None
    event.peer_id = None
    event.session_id = None
    event.data = SimpleNamespace(group_id="g1")
    assert _conversation_id(event) == "g1"


def test_conversation_id_falls_back_to_session_id() -> None:
    event = make_event(group_id=None)
    event.guild_id = None
    event.channel_id = None
    event.peer_id = None
    event.session_id = None
    event.data = SimpleNamespace()
    event.get_session_id.return_value = "session-1"
    assert _conversation_id(event) == "session-1"


def test_user_id_falls_back_to_event_attr() -> None:
    event = make_event()
    event.get_user_id.return_value = None
    event.user_id = "u1"
    assert _user_id(event) == "u1"


def test_user_id_falls_back_to_event_data() -> None:
    event = make_event()
    event.get_user_id.return_value = None
    event.user_id = None
    event.sender_id = None
    event.data = SimpleNamespace(user_id="du1")
    assert _user_id(event) == "du1"


def test_plain_text_uses_get_message_when_plaintext_empty(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
    event = make_event()
    event.get_plaintext.return_value = ""
    assert _plain_text(event) == "hello"


def test_plain_text_uses_event_message_attr(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
    event = make_event()
    event.get_plaintext.return_value = ""
    event.get_message.return_value = None
    event.message = "text-msg"
    assert _plain_text(event) == "text-msg"


def test_plain_text_uses_event_data_message(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
    event = make_event()
    event.get_plaintext.return_value = ""
    event.get_message.return_value = None
    event.message = None
    event.data = SimpleNamespace(message="data-msg", segments=[])
    assert _plain_text(event) == "data-msg"


def test_plain_text_returns_none_when_no_message(
    monkeypatch: pytest.MonkeyPatch,
    enabled_config: SimpleNamespace,
) -> None:
    monkeypatch.setattr(adapters, "plugin_config", enabled_config)
    event = make_event()
    event.get_plaintext.return_value = ""
    event.get_message.return_value = None
    event.message = None
    event.data = SimpleNamespace()
    assert _plain_text(event) is None


def test_jsonable_returns_repr_when_depth_exceeded() -> None:
    assert _jsonable("deep", depth=9) == repr("deep")


def test_jsonable_slotted_object_without_dict() -> None:
    class Slotted:
        __slots__ = ()

    result = _jsonable(Slotted())
    assert isinstance(result, str)
    assert "Slotted" in result


def test_json_summary_returns_none_for_none() -> None:
    assert _json_summary(None) is None


def test_json_summary_falls_back_when_jsonable_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapters, "_jsonable", MagicMock(side_effect=TypeError("boom")))
    result = _json_summary("x")
    assert isinstance(result, str)
    assert result == '"x"'


def test_raw_message_falls_back_to_event_message_attr() -> None:
    event = make_event()
    event.get_message.return_value = None
    event.message = "raw-msg"
    assert _raw_message(event) == '"raw-msg"'


def test_raw_message_falls_back_to_event_data() -> None:
    event = make_event()
    event.get_message.return_value = None
    event.message = None
    event.data = SimpleNamespace(message="data-raw", segments=[])
    assert _raw_message(event) == '"data-raw"'
