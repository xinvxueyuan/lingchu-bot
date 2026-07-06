"""Tests for the ``ai_api_key`` field on :class:`RuntimeConfig`.

Verifies code defaults, JSON5 dict loading, and env-var override priority
(`OS env > dotenv > JSON5 > code defaults`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nonebot.compat import type_validate_python

from src.plugins.nonebot_plugin_lingchu_bot.core.runtime_config import (
    RuntimeConfig,
    _env_overrides,
)

if TYPE_CHECKING:
    import pytest


def test_ai_api_key_defaults_to_none() -> None:
    """Code default for ``ai_api_key`` is ``None``."""
    config = RuntimeConfig()
    assert config.ai_api_key is None


def test_ai_api_key_loaded_from_dict() -> None:
    """``ai_api_key`` is populated when validating a JSON5-style dict."""
    config = type_validate_python(RuntimeConfig, {"ai_api_key": "sk-test123"})
    assert config.ai_api_key == "sk-test123"


def test_ai_api_key_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_env_overrides`` reads ``AI_API_KEY`` from the OS environment."""
    monkeypatch.setenv("AI_API_KEY", "sk-env456")
    try:
        overrides = _env_overrides({})
    finally:
        monkeypatch.delenv("AI_API_KEY", raising=False)

    assert overrides == {"ai_api_key": "sk-env456"}


def test_ai_api_key_env_overrides_json5(monkeypatch: pytest.MonkeyPatch) -> None:
    """OS env var wins over a JSON5 dict value when both are present."""
    monkeypatch.setenv("AI_API_KEY", "sk-env456")
    try:
        json5_dict = {"ai_api_key": "sk-json5-losing"}
        merged = json5_dict | _env_overrides({})
    finally:
        monkeypatch.delenv("AI_API_KEY", raising=False)

    config = type_validate_python(RuntimeConfig, merged)
    assert config.ai_api_key == "sk-env456"
