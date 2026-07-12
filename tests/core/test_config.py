from __future__ import annotations

from pathlib import Path
import platform
from typing import Any

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.config import (
    Config,
    InvalidInContainersError,
    UnexpectedInContainersTypeError,
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
