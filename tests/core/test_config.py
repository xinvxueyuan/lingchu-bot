from __future__ import annotations

import json
from pathlib import Path
import platform
from typing import Any

import aiofiles
import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.core import config as config_module
from src.plugins.nonebot_plugin_lingchu_bot.core.config import (
    Config,
    InvalidInContainersError,
    RuntimeConfig,
    RuntimeConfigError,
    UnexpectedInContainersTypeError,
    ensure_runtime_config_file,
    ensure_runtime_config_file_async,
    get_runtime_config,
    runtime_config_defaults,
)

EXPECTED_PLATFORM_INFO_KEYS = {
    "system",
    "release",
    "version",
    "machine",
    "processor",
    "python_version",
    "in_containers",
}


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        data_dir=tmp_path / "data",
        config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache",
    )


def _config_with(tmp_path: Path, **alias_kwargs: Any) -> Config:
    """Build a Config using validation-alias kwargs that pyright cannot resolve."""
    kwargs: dict[str, Any] = {
        "data_dir": tmp_path / "data",
        "config_dir": tmp_path / "config",
        "cache_dir": tmp_path / "cache",
        **alias_kwargs,
    }
    return Config(**kwargs)


def test_config_has_core_version_default(config: Config) -> None:
    assert config.core_version == "0.0.0.dev40"


def test_config_has_path_fields(config: Config) -> None:
    assert isinstance(config.data_dir, Path)
    assert isinstance(config.config_dir, Path)
    assert isinstance(config.cache_dir, Path)
    assert config.announcement_image_cache_dir is not None
    assert isinstance(config.announcement_image_cache_dir, Path)
    assert config.announcement_image_protocol_dir is None


def test_config_accepts_announcement_image_path_bridge(tmp_path: Path) -> None:
    config = _config_with(
        tmp_path,
        LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR=tmp_path / "announcement-images",
        LINGCHU_ANNOUNCEMENT_IMAGE_PROTOCOL_DIR="/lingchu/announcement-images",
    )

    assert config.announcement_image_cache_dir == tmp_path / "announcement-images"
    assert config.announcement_image_protocol_dir == "/lingchu/announcement-images"


def test_system_type_returns_windows(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    assert config.system_type == "Windows"


def test_system_type_returns_linux(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    assert config.system_type == "Linux"


def test_system_type_returns_darwin(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    assert config.system_type == "Darwin"


def test_system_type_returns_other_for_unknown(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "UnknownOS")
    assert config.system_type == "Other"


def test_is_windows_true(monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    assert config.is_windows is True
    assert config.is_linux is False
    assert config.is_macos is False


def test_is_linux_true(monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    assert config.is_linux is True
    assert config.is_windows is False
    assert config.is_macos is False


def test_is_macos_true(monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    assert config.is_macos is True
    assert config.is_windows is False
    assert config.is_linux is False


def test_get_platform_info_returns_expected_keys(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    info = config.get_platform_info()
    assert isinstance(info, dict)
    assert set(info) == EXPECTED_PLATFORM_INFO_KEYS
    assert info["system"] == "Linux"
    assert info["in_containers"] is False


def test_in_containers_defaults_to_false_when_not_configured(config: Config) -> None:
    assert config.in_containers is False


def test_in_containers_returns_true_when_configured(tmp_path: Path) -> None:
    config = _config_with(tmp_path, LINGCHU_IN_CONTAINERS=True)
    assert config.in_containers is True


def test_in_containers_returns_false_when_explicitly_false(tmp_path: Path) -> None:
    config = _config_with(tmp_path, LINGCHU_IN_CONTAINERS=False)
    assert config.in_containers is False


def test_in_containers_raises_for_string_value(tmp_path: Path) -> None:
    with pytest.raises(InvalidInContainersError):
        _config_with(tmp_path, LINGCHU_IN_CONTAINERS="true")


def test_in_containers_raises_for_unexpected_type(tmp_path: Path) -> None:
    with pytest.raises(UnexpectedInContainersTypeError):
        _config_with(tmp_path, LINGCHU_IN_CONTAINERS=123)


# --- Merged from test_runtime_config.py (Task 13: runtime_config → config) ---

DEFAULT_RETENTION_DAYS = 30
DEFAULT_SUMMARY_LIMIT = 500
DEFAULT_RECALL_COUNT = 10
TOML_SUMMARY_LIMIT = 12
ENV_SUMMARY_LIMIT = 42
DOTENV_SUMMARY_LIMIT = 64
OS_SUMMARY_LIMIT = 88
DEFAULT_AI_TIMEOUT = 60.0


def test_runtime_config_uses_code_defaults_without_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "_nonebot_runtime_overrides", dict)

    config = get_runtime_config(tmp_path / "missing.toml")

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


def test_runtime_config_ignores_legacy_json5_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "_nonebot_runtime_overrides", dict)
    legacy_file = tmp_path / "config.json5"
    legacy_file.write_text("{message_store_enabled: false}", encoding="utf-8")

    config = get_runtime_config(tmp_path / "config.toml")

    assert config.message_store_enabled is True


def test_runtime_config_reads_toml_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        rtoml.dumps({
            "message_store_enabled": False,
            "message_store_summary_limit": 12,
            "ai_provider": "openai",
            "ai_model": "gpt-4.1-mini",
            "ai_base_url": "https://example.test/v1",
            "ai_timeout": 9.5,
            "lingchu_adapter": "~milky",
            "future_field": "ignored",
        }),
        encoding="utf-8",
    )

    config = get_runtime_config(config_file)

    assert config.message_store_enabled is False
    assert config.message_store_summary_limit == TOML_SUMMARY_LIMIT
    assert config.ai_provider == "openai"
    assert config.ai_model == "gpt-4.1-mini"
    assert config.ai_base_url == "https://example.test/v1"
    assert config.ai_timeout == 9.5
    assert config.lingchu_adapter == "~milky"


def test_runtime_config_reads_lingchu_superusers_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        rtoml.dumps({
            "lingchu_superusers": {"userA": {"qq": 42, "telegram": "tg-user"}}
        }),
        encoding="utf-8",
    )

    config = get_runtime_config(config_file)

    assert config.lingchu_superusers == {"userA": {"qq": 42, "telegram": "tg-user"}}


def test_runtime_config_rejects_invalid_lingchu_superusers_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("LINGCHU_SUPERUSERS", "not-json")

    with pytest.raises(RuntimeConfigError):
        get_runtime_config(config_file)


def test_runtime_config_nonebot_env_overrides_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("message_store_summary_limit = 12\n", encoding="utf-8")
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT", str(ENV_SUMMARY_LIMIT))

    config = get_runtime_config(config_file)

    assert config.message_store_summary_limit == ENV_SUMMARY_LIMIT


def test_runtime_config_ai_env_overrides_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'ai_provider = "litellm"\nai_model = "toml-model"\nai_timeout = 12\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("LINGCHU_AI_PROVIDER", "openai")
    monkeypatch.setenv("LINGCHU_AI_MODEL", "env-model")
    monkeypatch.setenv("LINGCHU_AI_TIMEOUT", "7.5")

    config = get_runtime_config(config_file)

    assert config.ai_provider == "openai"
    assert config.ai_model == "env-model"
    assert config.ai_timeout == 7.5


def test_runtime_config_dotenv_overrides_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("message_store_summary_limit = 12\n", encoding="utf-8")
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        f"LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT={DOTENV_SUMMARY_LIMIT}\n",
        encoding="utf-8",
    )
    driver_config = config_module.get_driver().config
    monkeypatch.setattr(driver_config, "_env_file", dotenv_file)
    monkeypatch.delenv("LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT", raising=False)

    config = get_runtime_config(config_file)

    assert config.message_store_summary_limit == DOTENV_SUMMARY_LIMIT


def test_runtime_config_os_env_overrides_dotenv_and_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("message_store_summary_limit = 12\n", encoding="utf-8")
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        f"LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT={DOTENV_SUMMARY_LIMIT}\n",
        encoding="utf-8",
    )
    driver_config = config_module.get_driver().config
    monkeypatch.setattr(driver_config, "_env_file", dotenv_file)
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT", str(OS_SUMMARY_LIMIT))

    config = get_runtime_config(config_file)

    assert config.message_store_summary_limit == OS_SUMMARY_LIMIT


def test_ensure_runtime_config_file_creates_default_toml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"

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
    config_file = tmp_path / "config.toml"
    config_file.write_text("message_store_retention_days = 7\n", encoding="utf-8")

    ensure_runtime_config_file(config_file)

    assert "7" in config_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_ensure_runtime_config_file_async_creates_default_toml(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"

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
    config_file = tmp_path / "config.toml"
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("message_store_retention_days = 7\n")

    await ensure_runtime_config_file_async(config_file)

    async with aiofiles.open(config_file, encoding="utf-8") as f:
        assert "7" in await f.read()


def test_runtime_config_invalid_toml_includes_path(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("{broken", encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_rejects_invalid_field_type(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("message_store_retention_days = -1\n", encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_rejects_invalid_ai_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.toml"
    config_file.write_text('ai_provider = "unsupported"\n', encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_rejects_invalid_ai_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "_nonebot_runtime_overrides", dict)
    config_file = tmp_path / "config.toml"
    config_file.write_text("ai_timeout = 0\n", encoding="utf-8")

    with pytest.raises(RuntimeConfigError) as exc_info:
        get_runtime_config(config_file)

    assert str(config_file) in str(exc_info.value)


def test_runtime_config_defaults_do_not_contain_schema_metadata() -> None:
    defaults = runtime_config_defaults()

    assert "$schema" not in defaults


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
    schema_text = json.dumps(RuntimeConfig.model_json_schema())

    # Pydantic's model_json_schema() uses the first AliasChoices value as the
    # property name, so the schema advertises the LINGCHU_ env-style key.
    assert "LINGCHU_PROTECTED_SUBJECT_FEATURE_KEYS" in schema_text


def test_runtime_config_schema_documents_ai_fields() -> None:
    schema_text = json.dumps(RuntimeConfig.model_json_schema())

    # Pydantic's model_json_schema() uses the first AliasChoices value as the
    # property name, so the schema advertises the LINGCHU_ env-style keys.
    assert "LINGCHU_AI_PROVIDER" in schema_text
    assert "litellm" in schema_text
    assert "LINGCHU_AI_MODEL" in schema_text
    assert "LINGCHU_AI_BASE_URL" in schema_text
    assert "LINGCHU_AI_TIMEOUT" in schema_text


def test_env_overrides_prefixed_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LINGCHU_-prefixed env keys are read correctly."""
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_ENABLED", "false")
    config = get_runtime_config(tmp_path / "missing.toml")
    assert config.message_store_enabled is False
    monkeypatch.delenv("LINGCHU_MESSAGE_STORE_ENABLED", raising=False)


def test_env_overrides_ignores_legacy_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy unprefixed env keys are ignored; only LINGCHU_ prefix is read."""
    monkeypatch.delenv("LINGCHU_MESSAGE_STORE_ENABLED", raising=False)
    monkeypatch.setenv("MESSAGE_STORE_ENABLED", "false")
    config = get_runtime_config(tmp_path / "missing.toml")
    assert config.message_store_enabled is True  # code default, legacy key ignored
    monkeypatch.delenv("MESSAGE_STORE_ENABLED", raising=False)
