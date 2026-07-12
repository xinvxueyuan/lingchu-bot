"""Tests for the LLM chat nested subplugin configuration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.llm_chat import config


def test_chat_config_defaults_returns_json_serialized_defaults() -> None:
    """chat_config_defaults returns the JSON-serialized default ChatConfig."""
    defaults = config.chat_config_defaults()

    assert defaults == {"enabled": True, "system_prompt": "你是一个友好的群聊助手。"}


def test_chat_config_schema_contains_required_fields() -> None:
    """chat_config_schema returns a JSON schema with the ChatConfig properties."""
    schema = config.chat_config_schema()

    assert schema["type"] == "object"
    properties = schema["properties"]
    assert set(properties) == {"enabled", "system_prompt"}
    assert properties["enabled"]["type"] == "boolean"
    assert properties["enabled"]["default"] is True
    assert properties["system_prompt"]["type"] == "string"
    assert properties["system_prompt"]["default"] == "你是一个友好的群聊助手。"


def test_chat_config_constants_are_expected_basenames() -> None:
    """CONFIG_FILENAME and SCHEMA_FILENAME are the expected basenames."""
    assert config.CONFIG_FILENAME == "llm_chat.toml"
    assert config.SCHEMA_FILENAME == "llm_chat.schema.json"


def test_chat_config_model_defaults() -> None:
    """ChatConfig defaults to enabled with the standard Chinese system prompt."""
    value = config.ChatConfig()

    assert value.enabled is True
    assert value.system_prompt == "你是一个友好的群聊助手。"


def test_chat_config_model_ignores_extra_fields() -> None:
    """ChatConfig ignores unknown fields via ConfigDict(extra='ignore')."""
    value = config.ChatConfig.model_validate({
        "enabled": False,
        "system_prompt": "hi",
        "unknown": "ignored",
    })

    assert value.enabled is False
    assert value.system_prompt == "hi"
    assert not hasattr(value, "unknown")


def test_ensure_chat_config_files_creates_schema_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ensure_chat_config_files writes the schema file when it does not exist."""
    ensure_mock = MagicMock()
    monkeypatch.setattr(config, "ensure_subplugin_config_file", ensure_mock)

    schema_path = tmp_path / config.SCHEMA_FILENAME
    monkeypatch.setattr(
        config,
        "get_plugin_config_file",
        MagicMock(return_value=schema_path),
    )

    config.ensure_chat_config_files()

    ensure_mock.assert_called_once_with(
        config.CONFIG_FILENAME,
        config.chat_config_defaults(),
        schema_basename=config.SCHEMA_FILENAME,
    )
    assert schema_path.exists()
    written = json.loads(schema_path.read_text(encoding="utf-8"))
    assert written == config.chat_config_schema()


def test_ensure_chat_config_files_skips_schema_when_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ensure_chat_config_files leaves an existing schema file untouched."""
    monkeypatch.setattr(config, "ensure_subplugin_config_file", MagicMock())

    schema_path = tmp_path / config.SCHEMA_FILENAME
    pre_existing = {"existing": "schema"}
    schema_path.write_text(json.dumps(pre_existing), encoding="utf-8")

    monkeypatch.setattr(
        config,
        "get_plugin_config_file",
        MagicMock(return_value=schema_path),
    )

    config.ensure_chat_config_files()

    assert json.loads(schema_path.read_text(encoding="utf-8")) == pre_existing


def test_ensure_chat_config_files_creates_parent_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ensure_chat_config_files creates the parent directory if needed."""
    monkeypatch.setattr(config, "ensure_subplugin_config_file", MagicMock())

    nested_dir = tmp_path / "nested" / "config"
    schema_path = nested_dir / config.SCHEMA_FILENAME
    monkeypatch.setattr(
        config,
        "get_plugin_config_file",
        MagicMock(return_value=schema_path),
    )

    config.ensure_chat_config_files()

    assert nested_dir.is_dir()
    assert schema_path.exists()


def test_ensure_chat_config_files_uses_atomic_temp_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ensure_chat_config_files writes via a temp file then replaces it."""
    monkeypatch.setattr(config, "ensure_subplugin_config_file", MagicMock())

    schema_path = tmp_path / config.SCHEMA_FILENAME
    monkeypatch.setattr(
        config,
        "get_plugin_config_file",
        MagicMock(return_value=schema_path),
    )

    config.ensure_chat_config_files()

    expected_temp = schema_path.with_suffix(".tmp.json")
    assert not expected_temp.exists()
    assert schema_path.exists()


def test_ensure_chat_config_files_writes_utf8_non_ascii(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ensure_chat_config_files writes UTF-8 content preserving non-ASCII characters."""
    monkeypatch.setattr(config, "ensure_subplugin_config_file", MagicMock())

    schema_path = tmp_path / config.SCHEMA_FILENAME
    monkeypatch.setattr(
        config,
        "get_plugin_config_file",
        MagicMock(return_value=schema_path),
    )

    config.ensure_chat_config_files()

    raw = schema_path.read_text(encoding="utf-8")
    assert "你是一个友好的群聊助手。" in raw
    assert json.loads(raw) == config.chat_config_schema()


def test_get_chat_config_merges_defaults_with_loaded_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_chat_config returns a ChatConfig merging defaults with loaded values."""
    loaded = {"system_prompt": "overridden prompt", "ignored_extra": "ignored"}
    load_mock = MagicMock(return_value=loaded)
    monkeypatch.setattr(config, "load_subplugin_config", load_mock)

    result = config.get_chat_config()

    load_mock.assert_called_once_with(config.CONFIG_FILENAME)
    assert isinstance(result, config.ChatConfig)
    assert result.enabled is True
    assert result.system_prompt == "overridden prompt"


def test_get_chat_config_uses_defaults_when_load_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_chat_config uses defaults when the loaded config is empty."""
    monkeypatch.setattr(config, "load_subplugin_config", MagicMock(return_value={}))

    result = config.get_chat_config()

    assert isinstance(result, config.ChatConfig)
    assert result.enabled is True
    assert result.system_prompt == "你是一个友好的群聊助手。"


def test_get_chat_config_overrides_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_chat_config honors an overridden enabled flag from the loaded config."""
    monkeypatch.setattr(
        config,
        "load_subplugin_config",
        MagicMock(return_value={"enabled": False}),
    )

    result = config.get_chat_config()

    assert result.enabled is False
    assert result.system_prompt == "你是一个友好的群聊助手。"
