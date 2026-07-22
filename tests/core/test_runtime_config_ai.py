"""Tests for deployment-owned AI settings resolved by NoneBot."""

from pathlib import Path

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import config as config_module
from src.plugins.nonebot_plugin_lingchu_bot.core.config import (
    Config,
    get_runtime_config,
)


def test_ai_api_key_defaults_to_none(tmp_path: Path) -> None:
    config = Config(
        data_dir=tmp_path / "data",
        config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache",
    )
    assert config.ai_api_key is None


def test_ai_api_key_accepts_nonebot_aliases(tmp_path: Path) -> None:
    config = Config.model_validate({
        "data_dir": tmp_path / "data",
        "config_dir": tmp_path / "config",
        "cache_dir": tmp_path / "cache",
        "LINGCHU_AI_API_KEY": "test-key",
    })
    assert config.ai_api_key == "test-key"


def test_ai_api_key_comes_from_nonebot_plugin_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected = Config.model_validate({
        "data_dir": tmp_path / "data",
        "config_dir": tmp_path / "config",
        "cache_dir": tmp_path / "cache",
        "LINGCHU_AI_API_KEY": "resolved-key",
    })
    monkeypatch.setattr(config_module, "get_plugin_config", lambda _model: expected)

    assert get_runtime_config().ai_api_key == "resolved-key"
