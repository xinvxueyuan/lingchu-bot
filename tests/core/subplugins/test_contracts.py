from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import subplugins
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import contracts


async def test_complete_subplugin_chat_uses_managed_runtime_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.respond = AsyncMock(
        return_value=SimpleNamespace(text="result", raw=object())
    )
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )
    messages = [{"role": "user", "content": "describe"}]

    assert (
        await contracts.complete_subplugin_chat(messages, profile="child") == "result"
    )
    runtime.respond.assert_awaited_once_with(messages, profile="child")


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
    """complete_subplugin_chat_default forwards messages to the default profile."""
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.respond = AsyncMock(
        return_value=SimpleNamespace(text="result", raw=object())
    )
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )
    messages = [{"role": "user", "content": "hi"}]

    assert await contracts.complete_subplugin_chat_default(messages) == "result"
    runtime.respond.assert_awaited_once_with(messages, profile=None)


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
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.respond = AsyncMock(side_effect=contracts.LLMError("boom"))
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )

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
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.respond = AsyncMock(side_effect=original)
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )

    with pytest.raises(contracts.SubpluginLLMError) as exc_info:
        await contracts.complete_subplugin_chat_default([
            {"role": "user", "content": "hi"}
        ])
    assert exc_info.value is original


@pytest.mark.parametrize(
    ("response_text", "expected_error"),
    [
        (None, contracts.MissingLLMContentError),
        ("", contracts.EmptyLLMContentError),
    ],
)
async def test_complete_subplugin_chat_rejects_missing_response_text(
    monkeypatch: pytest.MonkeyPatch,
    response_text: str | None,
    expected_error: type[Exception],
) -> None:
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.respond = AsyncMock(
        return_value=SimpleNamespace(text=response_text, raw=object())
    )
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )

    with pytest.raises(contracts.SubpluginLLMError) as exc_info:
        await contracts.complete_subplugin_chat([{"role": "user", "content": "hi"}])
    assert isinstance(exc_info.value.__cause__, expected_error)


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


async def test_subplugin_web_search_contract_uses_runtime_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = [{"role": "user", "content": "visual facts"}]
    profile = SimpleNamespace(
        name="search",
        backend="litellm",
        model="search-model",
        base_url="https://example.test/v1",
    )
    raw = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    annotations=[
                        {
                            "url_citation": {
                                "url": "https://example.test/source",
                            }
                        }
                    ]
                )
            )
        ]
    )
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.profile = MagicMock(return_value=profile)
    runtime.litellm = MagicMock(return_value=object())
    runtime.respond = AsyncMock(
        return_value=SimpleNamespace(text='["blue coat"]', raw=raw)
    )
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )
    monkeypatch.setattr(
        contracts,
        "probe_capability",
        MagicMock(return_value=SimpleNamespace(support="supported")),
    )

    assert await contracts.complete_subplugin_web_search(
        messages, profile="search"
    ) == contracts.WebSearchResult(
        text='["blue coat"]', sources=("https://example.test/source",)
    )
    runtime.profile.assert_called_once_with("search")
    runtime.litellm.assert_called_once_with("search")
    runtime.respond.assert_awaited_once_with(
        messages, profile="search", tools=[{"type": "web_search"}]
    )


async def test_subplugin_web_search_contract_skips_unsupported_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.profile = MagicMock(
        return_value=SimpleNamespace(name="default", backend="openai")
    )
    runtime.respond = AsyncMock()
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )

    assert await contracts.complete_subplugin_web_search([]) is None
    runtime.respond.assert_not_awaited()


async def test_subplugin_web_search_contract_skips_unsupported_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.profile = MagicMock(
        return_value=SimpleNamespace(name="search", backend="litellm")
    )
    runtime.litellm = MagicMock(return_value=object())
    runtime.respond = AsyncMock()
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )
    monkeypatch.setattr(
        contracts,
        "probe_capability",
        MagicMock(return_value=SimpleNamespace(support="unsupported")),
    )

    assert await contracts.complete_subplugin_web_search([]) is None
    runtime.respond.assert_not_awaited()


async def test_subplugin_web_search_contract_soft_fails_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = MagicMock(spec=contracts.LLMRuntime)
    runtime.profile = MagicMock(
        return_value=SimpleNamespace(name="search", backend="litellm")
    )
    runtime.litellm = MagicMock(return_value=object())
    runtime.respond = AsyncMock(side_effect=RuntimeError("provider down"))
    monkeypatch.setattr(
        contracts, "get_subplugin_llm_runtime", MagicMock(return_value=runtime)
    )
    monkeypatch.setattr(
        contracts,
        "probe_capability",
        MagicMock(return_value=SimpleNamespace(support="supported")),
    )

    assert await contracts.complete_subplugin_web_search([]) is None


def test_web_search_sources_filter_unsafe_and_deduplicate() -> None:
    annotations = [
        {"url_citation": {"url": "https://example.test/ok?ref=public"}},
        {"url_citation": {"url": "https://example.test/ok?ref=public"}},
        {"url_citation": {"url": "http://localhost/private"}},
        {"url_citation": {"url": "https://example.test/secret?api_key=hidden"}},
        {"url_citation": {"url": "https://user@example.test/credentials"}},
        {"url": "https://example.test/fallback"},
        {"url": "ftp://example.test/file"},
        {"url": "https://example.test/fragment#part"},
        {"url": "https://example.test/control\n"},
    ]
    raw = SimpleNamespace(
        choices=[SimpleNamespace(message={"annotations": annotations})]
    )

    assert contracts._extract_source_urls(raw) == (
        "https://example.test/ok?ref=public",
        "https://example.test/fallback",
    )


def test_web_search_sources_use_provider_specific_annotations() -> None:
    raw = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message={
                    "provider_specific_fields": {
                        "annotations": [
                            {"url": "https://example.test/provider-specific"}
                        ]
                    }
                }
            )
        ]
    )

    assert contracts._extract_source_urls(raw) == (
        "https://example.test/provider-specific",
    )


def test_web_search_sources_ignore_malformed_provider_payload() -> None:
    class BrokenResponse:
        @property
        def choices(self) -> object:
            raise RuntimeError("broken")

    assert contracts._extract_source_urls(BrokenResponse()) == ()


@pytest.mark.parametrize(
    "raw",
    [
        object(),
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=[SimpleNamespace(message={})]),
        SimpleNamespace(choices=[SimpleNamespace(message={"annotations": "bad"})]),
    ],
)
def test_web_search_sources_ignore_missing_or_non_sequence_annotations(
    raw: object,
) -> None:
    assert contracts._extract_source_urls(raw) == ()


def test_web_search_sources_are_bounded() -> None:
    annotations = [
        {"url": f"https://example.test/source/{index}"}
        for index in range(contracts.MAX_WEB_SEARCH_SOURCES + 8)
    ]
    raw = SimpleNamespace(
        choices=[SimpleNamespace(message={"annotations": annotations})]
    )

    sources = contracts._extract_source_urls(raw)

    assert len(sources) == contracts.MAX_WEB_SEARCH_SOURCES
    assert sources[-1] == (
        f"https://example.test/source/{contracts.MAX_WEB_SEARCH_SOURCES - 1}"
    )


@pytest.mark.parametrize(
    "value",
    [
        "https://example.test/" + ("a" * contracts.MAX_SOURCE_URL_LENGTH),
        "https://[bad",
        "https://127.0.0.1/source",
        "https://metadata.google.internal/source",
        "https://example.localhost/source",
        "https://example.test/source?broken",
        "https://example.test/source?token=public",
        "https://example.test/source?q=Bearer%20secret",
    ],
)
def test_safe_source_url_rejects_unsafe_values(value: str) -> None:
    assert contracts._safe_source_url(value) is None


def test_web_search_contract_is_public() -> None:
    assert "WebSearchResult" in contracts.__all__
    assert "complete_subplugin_web_search" in contracts.__all__


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


def test_register_subplugin_handler_delegates_without_wrapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matcher = object()

    def passthrough(func: object) -> object:
        return func

    selected = MagicMock(return_value=passthrough)
    monkeypatch.setattr(contracts, "selected_adapter_handle", selected)

    async def handler(prompt: list[str]) -> None:
        _ = prompt

    registered = contracts.register_subplugin_handler(
        matcher,
        "test_cmd",
        "~onebot.v11",
        bypass_gate=True,
    )(handler)

    assert registered is handler
    selected.assert_called_once_with(
        matcher,
        "~onebot.v11",
        "test_cmd",
        bypass_gate=True,
        bypass_silent=False,
    )
