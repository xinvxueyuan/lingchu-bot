from dataclasses import FrozenInstanceError
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import subplugins
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import contracts


async def test_complete_subplugin_chat_forwards_explicit_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete_chat = AsyncMock(return_value="result")
    monkeypatch.setattr(contracts, "complete_chat", complete_chat)
    options = contracts.LLMOptions(
        provider="litellm",
        model="child-model",
        base_url=None,
        api_key=None,
        timeout=8.0,
    )
    messages = [{"role": "user", "content": "describe"}]

    assert (
        await contracts.complete_subplugin_chat(messages, options=options) == "result"
    )
    complete_chat.assert_awaited_once_with(messages, options=options)


def test_register_and_collect_subplugin_menu_features() -> None:
    """register_subplugin_menu_feature stores features; collect returns them."""
    from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import (
        collect_subplugin_menu_features,
        register_subplugin_menu_feature,
        reset_subplugin_menu_features,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import (
        LocalizedText,
        MenuAvailability,
        MenuFeature,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.platforms import PlatformCapability

    original = collect_subplugin_menu_features()
    try:
        reset_subplugin_menu_features()
        feature = MenuFeature(
            "test-feature",
            "test_cmd",
            "entertainment",
            LocalizedText("测试", "Test"),
            LocalizedText("<arg>", "<arg>"),
            PlatformCapability.LLM_CHAT,
            (MenuAvailability("qq", "~onebot.v11"),),
        )
        register_subplugin_menu_feature(feature)
        collected = collect_subplugin_menu_features()
        assert feature in collected
        assert len(collected) == 1
    finally:
        reset_subplugin_menu_features()
        for feature in original:
            register_subplugin_menu_feature(feature)


def test_reset_subplugin_menu_features_clears_registry() -> None:
    """reset_subplugin_menu_features clears all registered features."""
    from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import (
        collect_subplugin_menu_features,
        register_subplugin_menu_feature,
        reset_subplugin_menu_features,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import (
        LocalizedText,
        MenuAvailability,
        MenuFeature,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.platforms import PlatformCapability

    original = collect_subplugin_menu_features()
    try:
        reset_subplugin_menu_features()
        feature = MenuFeature(
            "tmp-feature",
            "test_cmd",
            "entertainment",
            LocalizedText("临时", "Temp"),
            LocalizedText("", ""),
            PlatformCapability.LLM_CHAT,
            (MenuAvailability("qq", "~onebot.v11"),),
        )
        register_subplugin_menu_feature(feature)
        assert len(collect_subplugin_menu_features()) == 1
        reset_subplugin_menu_features()
        assert collect_subplugin_menu_features() == ()
    finally:
        reset_subplugin_menu_features()
        for feature in original:
            register_subplugin_menu_feature(feature)


def test_subplugin_llm_error_subclasses_llm_error() -> None:
    """SubpluginLLMError is an LLMError subclass and preserves its message."""
    assert issubclass(contracts.SubpluginLLMError, contracts.LLMError)
    err = contracts.SubpluginLLMError("boom")
    assert isinstance(err, contracts.LLMError)
    assert str(err) == "boom"


async def test_complete_subplugin_chat_default_uses_default_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """complete_subplugin_chat_default forwards messages without an options kwarg."""
    complete_chat = AsyncMock(return_value="result")
    monkeypatch.setattr(contracts, "complete_chat", complete_chat)
    messages = [{"role": "user", "content": "hi"}]

    assert await contracts.complete_subplugin_chat_default(messages) == "result"
    complete_chat.assert_awaited_once_with(messages)
    assert "options" not in complete_chat.call_args.kwargs


def test_default_chat_contract_is_public() -> None:
    assert "complete_subplugin_chat_default" in contracts.__all__


def test_managed_llm_runtime_getter_is_exported_by_parent_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = MagicMock(spec=contracts.LLMRuntime)
    getter = MagicMock(return_value=runtime)
    monkeypatch.setattr(contracts, "get_llm_runtime", getter, raising=False)

    assert contracts.get_subplugin_llm_runtime() is runtime
    assert subplugins.get_subplugin_llm_runtime is contracts.get_subplugin_llm_runtime
    assert "get_subplugin_llm_runtime" in contracts.__all__
    assert "get_subplugin_llm_runtime" in subplugins.__all__


async def test_complete_subplugin_chat_default_wraps_llm_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """complete_subplugin_chat_default wraps LLMError as SubpluginLLMError."""
    complete_chat = AsyncMock(side_effect=contracts.LLMError("boom"))
    monkeypatch.setattr(contracts, "complete_chat", complete_chat)

    with pytest.raises(contracts.SubpluginLLMError) as exc_info:
        await contracts.complete_subplugin_chat_default([
            {"role": "user", "content": "hi"}
        ])
    assert isinstance(exc_info.value.__cause__, contracts.LLMError)


async def test_complete_subplugin_chat_default_reraises_subplugin_llm_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SubpluginLLMError is re-raised as-is, not double-wrapped."""
    original = contracts.SubpluginLLMError("nested")
    complete_chat = AsyncMock(side_effect=original)
    monkeypatch.setattr(contracts, "complete_chat", complete_chat)

    with pytest.raises(contracts.SubpluginLLMError) as exc_info:
        await contracts.complete_subplugin_chat_default([
            {"role": "user", "content": "hi"}
        ])
    assert exc_info.value is original


def test_subplugin_trigger_is_frozen_dataclass() -> None:
    """SubpluginTrigger is a frozen dataclass with primary and aliases fields."""
    from dataclasses import fields, is_dataclass

    assert is_dataclass(contracts.SubpluginTrigger)
    field_names = {f.name for f in fields(contracts.SubpluginTrigger)}
    assert field_names == {"primary", "aliases"}

    trigger = contracts.SubpluginTrigger(primary="cmd", aliases=frozenset({"a", "b"}))
    assert trigger.primary == "cmd"
    assert trigger.aliases == frozenset({"a", "b"})

    with pytest.raises(FrozenInstanceError):
        setattr(trigger, "primary", "other")  # noqa: B010 - intentional frozen-dataclass mutation test


def test_get_subplugin_trigger_for_chat() -> None:
    """get_subplugin_trigger('chat') returns a SubpluginTrigger from the registry."""
    trigger = contracts.get_subplugin_trigger("chat")
    assert isinstance(trigger, contracts.SubpluginTrigger)
    assert isinstance(trigger.primary, str)
    assert trigger.primary
    assert isinstance(trigger.aliases, frozenset)


def test_get_subplugin_trigger_for_novelai_image() -> None:
    """get_subplugin_trigger('novelai_image') returns locale-resolved primary/aliases."""
    trigger = contracts.get_subplugin_trigger("novelai_image")
    assert isinstance(trigger, contracts.SubpluginTrigger)
    assert isinstance(trigger.primary, str)
    assert trigger.primary
    assert isinstance(trigger.aliases, frozenset)
    assert trigger.aliases


def test_resolve_default_llm_options_reads_runtime_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_default_llm_options builds LLMOptions from plugin_config fields."""
    fake_config = SimpleNamespace(
        ai_provider="openai",
        ai_model="gpt-4",
        ai_base_url="http://example.com",
        ai_api_key="secret",
        ai_timeout=30.0,
    )
    monkeypatch.setattr(contracts, "plugin_config", fake_config)

    options = contracts.resolve_default_llm_options()

    assert isinstance(options, contracts.LLMOptions)
    assert options.provider == "openai"
    assert options.model == "gpt-4"
    assert options.base_url == "http://example.com"
    assert options.api_key == "secret"
    assert options.timeout == 30.0


async def test_subplugin_web_search_contract_forwards_same_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    options = contracts.LLMOptions(
        provider="litellm",
        model="search-model",
        base_url="https://example.test/v1",
        api_key="secret",
        timeout=12.0,
    )
    messages = [{"role": "user", "content": "visual facts"}]
    result = contracts.WebSearchResult(
        text='["blue coat"]', sources=("https://example.test/source",)
    )
    complete = AsyncMock(return_value=result)
    monkeypatch.setattr(contracts, "complete_with_web_search", complete)

    monkeypatch.setattr(contracts, "supports_web_search", MagicMock(return_value=False))
    assert contracts.subplugin_supports_web_search(options) is False
    monkeypatch.setattr(contracts, "supports_web_search", MagicMock(return_value=True))
    assert contracts.subplugin_supports_web_search(options) is True
    assert (
        await contracts.complete_subplugin_web_search(messages, options=options)
        == result
    )
    complete.assert_awaited_once_with(messages, options=options)


def test_web_search_contract_is_public() -> None:
    assert "WebSearchResult" in contracts.__all__
    assert "complete_subplugin_web_search" in contracts.__all__
    assert "subplugin_supports_web_search" in contracts.__all__


def test_ensure_subplugin_config_file_delegates_to_toml_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ensure_subplugin_config_file resolves the config path and forwards to toml_store."""
    ensure_mock = MagicMock()
    monkeypatch.setattr(contracts, "ensure_toml_dict_file_sync", ensure_mock)
    expected_path = Path("/fake/config/sub.toml")
    monkeypatch.setattr(
        contracts, "get_plugin_config_file", MagicMock(return_value=expected_path)
    )

    defaults = {"key": "value"}
    contracts.ensure_subplugin_config_file(
        "sub.toml", defaults, schema_basename="schema.json"
    )

    ensure_mock.assert_called_once_with(
        expected_path, defaults, schema_basename="schema.json"
    )


def test_ensure_subplugin_config_file_defaults_schema_basename_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ensure_subplugin_config_file passes schema_basename=None when omitted."""
    ensure_mock = MagicMock()
    monkeypatch.setattr(contracts, "ensure_toml_dict_file_sync", ensure_mock)
    expected_path = Path("/fake/config/sub.toml")
    monkeypatch.setattr(
        contracts, "get_plugin_config_file", MagicMock(return_value=expected_path)
    )

    contracts.ensure_subplugin_config_file("sub.toml", {"key": "value"})

    ensure_mock.assert_called_once_with(
        expected_path, {"key": "value"}, schema_basename=None
    )


def test_load_subplugin_config_delegates_to_toml_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """load_subplugin_config resolves the config path and forwards to toml_store."""
    expected_data = {"key": "value"}
    load_mock = MagicMock(return_value=expected_data)
    monkeypatch.setattr(contracts, "load_toml_dict_sync", load_mock)
    expected_path = Path("/fake/config/sub.toml")
    monkeypatch.setattr(
        contracts, "get_plugin_config_file", MagicMock(return_value=expected_path)
    )

    result = contracts.load_subplugin_config("sub.toml")

    load_mock.assert_called_once_with(expected_path)
    assert result is expected_data


def test_image_message_wraps_message_segment_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """image_message delegates to MessageSegment.image with raw bytes."""
    from nonebot.adapters.onebot.v11 import MessageSegment

    sentinel = MagicMock(name="image_segment")
    image_mock = MagicMock(return_value=sentinel)
    monkeypatch.setattr(MessageSegment, "image", image_mock)

    result = contracts.image_message(b"image-bytes")

    image_mock.assert_called_once_with(b"image-bytes")
    assert result is sentinel


async def test_register_subplugin_handler_filters_bot_event_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """register_subplugin_handler wraps func to filter bot/event kwargs."""
    captured: dict[str, object] = {}

    def passthrough(func: object) -> object:
        return func

    def fake_selected_adapter_handle(
        matcher: object,
        adapter_id: str,
        command_key: str | None,
        *,
        bypass_gate: bool,
        bypass_silent: bool,
    ) -> object:
        captured["matcher"] = matcher
        captured["adapter_id"] = adapter_id
        captured["command_key"] = command_key
        captured["bypass_gate"] = bypass_gate
        captured["bypass_silent"] = bypass_silent
        return passthrough

    monkeypatch.setattr(
        contracts, "selected_adapter_handle", fake_selected_adapter_handle
    )

    matcher = object()
    decorator = contracts.register_subplugin_handler(
        matcher, "test_cmd", "~onebot.v11", bypass_gate=True, bypass_silent=False
    )
    assert callable(decorator)

    received: dict[str, object] = {}

    async def handler(prompt: list[str]) -> str:
        received["prompt"] = prompt
        return "ok"

    wrapped = decorator(handler)
    assert callable(wrapped)

    result = await wrapped(prompt=["hi"], bot=object(), event=object())
    assert result == "ok"
    assert received == {"prompt": ["hi"]}

    assert captured["matcher"] is matcher
    assert captured["adapter_id"] == "~onebot.v11"
    assert captured["command_key"] == "test_cmd"
    assert captured["bypass_gate"] is True
    assert captured["bypass_silent"] is False


def test_register_subplugin_handler_appends_bot_event_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wrapper signature appends bot/event params for NoneBot dependency injection."""

    def passthrough(func: object) -> object:
        return func

    monkeypatch.setattr(
        contracts, "selected_adapter_handle", MagicMock(return_value=passthrough)
    )

    decorator = contracts.register_subplugin_handler(
        object(), "test_cmd", "~onebot.v11"
    )

    async def handler(prompt: list[str]) -> None:
        pass

    wrapped = decorator(handler)
    params = list(inspect.signature(wrapped).parameters.keys())
    assert params == ["prompt", "bot", "event"]
