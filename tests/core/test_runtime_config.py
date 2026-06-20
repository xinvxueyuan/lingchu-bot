from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import runtime_config as runtime_module
from src.plugins.nonebot_plugin_lingchu_bot.core.runtime_config import (
    RuntimeConfigError,
    ensure_runtime_config_file,
    ensure_runtime_config_file_async,
    get_runtime_config,
)

if TYPE_CHECKING:
    from pathlib import Path


DEFAULT_RETENTION_DAYS = 30
DEFAULT_SUMMARY_LIMIT = 500
JSON_SUMMARY_LIMIT = 12
ENV_SUMMARY_LIMIT = 42
DOTENV_SUMMARY_LIMIT = 64
OS_SUMMARY_LIMIT = 88


def test_runtime_config_uses_code_defaults_without_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_module, "_nonebot_runtime_overrides", dict)

    config = get_runtime_config(tmp_path / "missing.json5")

    assert config.message_store_enabled is True
    assert config.message_store_retention_days == DEFAULT_RETENTION_DAYS
    assert config.message_store_summary_limit == DEFAULT_SUMMARY_LIMIT
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
          lingchu_adapter: "~milky",
          future_field: "ignored",
        }
        """,
        encoding="utf-8",
    )

    config = get_runtime_config(config_file)

    assert config.message_store_enabled is False
    assert config.message_store_summary_limit == JSON_SUMMARY_LIMIT
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
    config_file.write_text("{message_store_retention_days: 7}", encoding="utf-8")

    await ensure_runtime_config_file_async(config_file)

    assert "7" in config_file.read_text(encoding="utf-8")


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
