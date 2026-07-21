"""Tests for the ``ai_api_key`` field on :class:`RuntimeConfig`.

Verifies code defaults, TOML dict loading, and env-var override priority
(`OS env > dotenv > TOML > code defaults`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nonebot.compat import type_validate_python
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.config import (
    RuntimeConfig,
    _env_overrides,
)


@pytest.fixture
def config(tmp_path: Path) -> RuntimeConfig:
    """Build a Config without triggering localstore plugin detection."""
    return RuntimeConfig(
        data_dir=tmp_path / "data",
        config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache",
    )


def _config_from_dict(tmp_path: Path, toml_dict: dict[str, Any]) -> RuntimeConfig:
    """Validate a TOML-style dict into a Config with explicit path fields."""
    merged: dict[str, Any] = {
        "data_dir": tmp_path / "data",
        "config_dir": tmp_path / "config",
        "cache_dir": tmp_path / "cache",
        **toml_dict,
    }
    return type_validate_python(RuntimeConfig, merged)


def test_ai_api_key_defaults_to_none(config: RuntimeConfig) -> None:
    """Code default for ``ai_api_key`` is ``None``."""
    assert config.ai_api_key is None


def test_ai_api_key_loaded_from_dict(tmp_path: Path) -> None:
    """``ai_api_key`` is populated when validating a TOML-style dict."""
    config = _config_from_dict(tmp_path, {"ai_api_key": "sk-test123"})
    assert config.ai_api_key == "sk-test123"


def test_ai_api_key_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_env_overrides`` reads ``LINGCHU_AI_API_KEY`` from the OS environment."""
    monkeypatch.setenv("LINGCHU_AI_API_KEY", "sk-env456")
    try:
        overrides = _env_overrides({})
    finally:
        monkeypatch.delenv("LINGCHU_AI_API_KEY", raising=False)

    assert overrides == {"ai_api_key": "sk-env456"}


def test_ai_api_key_env_overrides_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OS env var wins over a TOML dict value when both are present."""
    monkeypatch.setenv("LINGCHU_AI_API_KEY", "sk-env456")
    try:
        toml_dict = {"ai_api_key": "sk-toml-losing"}
        merged = toml_dict | _env_overrides({})
    finally:
        monkeypatch.delenv("LINGCHU_AI_API_KEY", raising=False)

    config = _config_from_dict(tmp_path, merged)
    assert config.ai_api_key == "sk-env456"
