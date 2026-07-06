from __future__ import annotations

from typing import TYPE_CHECKING

import aiofiles
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import runtime_config as runtime_module
from src.plugins.nonebot_plugin_lingchu_bot.core.runtime_config import (
    CONFIG_SCHEMA_BASENAME,
    RuntimeConfigError,
    ensure_runtime_config_file,
    ensure_runtime_config_file_async,
    get_runtime_config,
    runtime_config_defaults,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.schemas import CONFIG_SCHEMA_TEXT

if TYPE_CHECKING:
    from pathlib import Path


DEFAULT_RETENTION_DAYS = 30
DEFAULT_SUMMARY_LIMIT = 500
DEFAULT_RECALL_COUNT = 10
JSON_SUMMARY_LIMIT = 12
ENV_SUMMARY_LIMIT = 42
DOTENV_SUMMARY_LIMIT = 64
OS_SUMMARY_LIMIT = 88
DEFAULT_AI_TIMEOUT = 60.0


def test_runtime_config_uses_code_defaults_without_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_module, "_nonebot_runtime_overrides", dict)

    config = get_runtime_config(tmp_path / "missing.json5")

    assert config.message_store_enabled is True
    assert config.message_store_retention_days == DEFAULT_RETENTION_DAYS
    assert config.message_store_summary_limit == DEFAULT_SUMMARY_LIMIT
    assert config.recall_message_default_count == DEFAULT_RECALL_COUNT
    assert config.ai_provider == "litellm"
    assert config.ai_model == "gpt-4o-mini"
    assert config.ai_base_url is None
    assert config.ai_timeout == DEFAULT_AI_TIMEOUT
    assert "recall_message" in config.protected_subject_feature_keys
    assert config.lingchu_adapter is None


def test_runtime_config_reads_json5_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.json5"
    config_file.write_text(
        """
        {
          message_store_enabled: false,
          message_store_summary_limit: 12,
          ai_provider: "openai",
          ai_model: "gpt-4.1-mini",
          ai_base_url: "https://example.test/v1",
          ai_timeout: 9.5,
          lingchu_adapter: "~milky",
          future_field: "ignored",
        }
        """,
        encoding="utf-8",
    )

    config = get_runtime_config(config_file)

    assert config.message_store_enabled is False
    assert config.message_store_summary_limit == JSON_SUMMARY_LIMIT
    assert config.ai_provider == "openai"
    assert config.ai_model == "gpt-4.1-mini"
    assert config.ai_base_url == "https://example.test/v1"
    assert config.ai_timeout == 9.5
    assert config.lingchu_adapter == "~milky"


def test_runtime_config_reads_lingchu_superusers_json5(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.json5"
    config_file.write_text(
        '{lingchu_superusers: {userA: {qq: 42, telegram: "tg-user"}}}',
        encoding="utf-8",
    )

    config = get_runtime_config(config_file)

    assert config.lingchu_superusers == {"userA": {"qq": 42, "telegram": "tg-user"}}


def test_runtime_config_rejects_invalid_lingchu_superusers_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LINGCHU_SUPERUSERS", "not-json")

    with pytest.raises(RuntimeConfigError):
        get_runtime_config(config_file)


def test_runtime_config_nonebot_env_overrides_json5(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{message_store_summary_limit: 12}", encoding="utf-8")
    monkeypatch.setenv("MESSAGE_STORE_SUMMARY_LIMIT", str(ENV_SUMMARY_LIMIT))

    config = get_runtime_config(config_file)

    assert config.message_store_summary_limit == ENV_SUMMARY_LIMIT


def test_runtime_config_ai_env_overrides_json5(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text(
        '{ai_provider: "litellm", ai_model: "json-model", ai_timeout: 12}',
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("AI_MODEL", "env-model")
    monkeypatch.setenv("AI_TIMEOUT", "7.5")

    config = get_runtime_config(config_file)

    assert config.ai_provider == "openai"
    assert config.ai_model == "env-model"
    assert config.ai_timeout == 7.5


def test_runtime_config_dotenv_overrides_json5(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{message_store_summary_limit: 12}", encoding="utf-8")
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        f"MESSAGE_STORE_SUMMARY_LIMIT={DOTENV_SUMMARY_LIMIT}\n",
        encoding="utf-8",
    )
    driver_config = runtime_module.get_driver().config
    monkeypatch.setattr(driver_config, "_env_file", dotenv_file)
    monkeypatch.delenv("MESSAGE_STORE_SUMMARY_LIMIT", raising=False)

    config = get_runtime_config(config_file)

    assert config.message_store_summary_limit == DOTENV_SUMMARY_LIMIT


def test_runtime_config_os_env_overrides_dotenv_and_json5(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{message_store_summary_limit: 12}", encoding="utf-8")
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        f"MESSAGE_STORE_SUMMARY_LIMIT={DOTENV_SUMMARY_LIMIT}\n",
        encoding="utf-8",
    )
    driver_config = runtime_module.get_driver().config
    monkeypatch.setattr(driver_config, "_env_file", dotenv_file)
    monkeypatch.setenv("MESSAGE_STORE_SUMMARY_LIMIT", str(OS_SUMMARY_LIMIT))

    config = get_runtime_config(config_file)

    assert config.message_store_summary_limit == OS_SUMMARY_LIMIT


def test_ensure_runtime_config_file_creates_default_json5(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"

    created = ensure_runtime_config_file(config_file)

    assert created == config_file
    assert config_file.exists()
    assert (
        get_runtime_config(config_file).message_store_retention_days
        == DEFAULT_RETENTION_DAYS
    )


def test_ensure_runtime_config_file_does_not_overwrite_existing(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{message_store_retention_days: 7}", encoding="utf-8")

    ensure_runtime_config_file(config_file)

    assert "7" in config_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_ensure_runtime_config_file_async_creates_default_json5(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.json5"

    created = await ensure_runtime_config_file_async(config_file)

    assert created == config_file
    assert config_file.exists()
    assert (
        get_runtime_config(config_file).message_store_retention_days
        == DEFAULT_RETENTION_DAYS
    )


@pytest.mark.asyncio
async def test_ensure_runtime_config_file_async_does_not_overwrite_existing(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.json5"
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("{message_store_retention_days: 7}")

    await ensure_runtime_config_file_async(config_file)

    async with aiofiles.open(config_file, encoding="utf-8") as f:
        assert "7" in await f.read()


def test_runtime_config_invalid_json5_includes_path(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{broken", encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_rejects_invalid_field_type(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{message_store_retention_days: -1}", encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_rejects_invalid_ai_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.json5"
    config_file.write_text('{ai_provider: "unsupported"}', encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_rejects_invalid_ai_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.json5"
    config_file.write_text("{ai_timeout: 0}", encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_defaults_contain_schema_basename() -> None:
    """Default payloads embed the schema reference as a bare basename."""
    defaults = runtime_config_defaults()

    assert defaults["$schema"] == CONFIG_SCHEMA_BASENAME
    assert "/" not in defaults["$schema"]
    assert "\\" not in defaults["$schema"]


def test_runtime_config_defaults_contain_whitelist_gate_keys() -> None:
    defaults = runtime_config_defaults()

    assert "protected_subject_feature_keys" in defaults
    assert set(defaults["protected_subject_feature_keys"]) >= {
        "kick_member",
        "block_member",
        "global_block_member",
        "member_mute",
        "recall_message",
        "remote_kick",
        "remote_block",
    }


def test_runtime_config_schema_documents_whitelist_gate() -> None:
    assert "protected_subject_feature_keys" in CONFIG_SCHEMA_TEXT
    assert "handle whitelist gate" in CONFIG_SCHEMA_TEXT


def test_runtime_config_schema_documents_ai_fields() -> None:
    assert "ai_provider" in CONFIG_SCHEMA_TEXT
    assert "litellm" in CONFIG_SCHEMA_TEXT
    assert "ai_model" in CONFIG_SCHEMA_TEXT
    assert "ai_base_url" in CONFIG_SCHEMA_TEXT
    assert "ai_timeout" in CONFIG_SCHEMA_TEXT


def test_runtime_config_user_schema_overrides_default(
    tmp_path: Path,
) -> None:
    """A user-provided ``$schema`` wins over the default basename."""
    config_file = tmp_path / "config.json5"
    config_file.write_text(
        '{"$schema": "custom.schema.json5", "message_store_enabled": false}',
        encoding="utf-8",
    )

    raw = runtime_config_defaults() | runtime_module.load_runtime_json_defaults(
        config_file
    )

    assert raw["$schema"] == "custom.schema.json5"
    assert raw["message_store_enabled"] is False
