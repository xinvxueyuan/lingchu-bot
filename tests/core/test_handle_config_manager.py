"""Tests for read-only handle configuration loading and explicit updates."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.core import (
    handle_config_manager as manager_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfigManager,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import (
    TOMLFileReadError,
)


@pytest.fixture
def manager_and_config_dir(
    tmp_path: Path,
) -> Generator[tuple[HandleConfigManager, Path]]:
    """Provide an isolated manager and localstore-backed config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    manager = HandleConfigManager()
    manager.clear_cache()
    with patch.object(
        manager_module,
        "get_plugin_config_file",
        side_effect=lambda filename: config_dir / filename,
    ):
        yield manager, config_dir
    manager.clear_cache()


@pytest.mark.asyncio
async def test_get_config_uses_typed_defaults_without_creating_missing_file(
    manager_and_config_dir: tuple[HandleConfigManager, Path],
) -> None:
    """A missing handle config is loaded in memory and remains missing."""
    manager, config_dir = manager_and_config_dir

    config = await manager.get_config("kick_member")

    assert config.enabled is True
    assert config.defaults["require_reason"] is False
    assert not (config_dir / "kick_member.toml").exists()


@pytest.mark.asyncio
async def test_update_config_persists_explicit_changes(
    manager_and_config_dir: tuple[HandleConfigManager, Path],
) -> None:
    """An explicit update creates and persists the localstore config file."""
    manager, config_dir = manager_and_config_dir
    config_file = config_dir / "kick_member.toml"

    await manager.update_config(
        "kick_member",
        {"enabled": False, "policies": {"role": "admin"}},
    )

    payload = rtoml.loads(config_file.read_text(encoding="utf-8"))
    assert payload["enabled"] is False
    assert payload["policies"] == {"role": "admin"}
    manager.clear_cache()
    config = await manager.get_config("kick_member")
    assert config.enabled is False
    assert config.policies == {"role": "admin"}


@pytest.mark.asyncio
async def test_get_config_uses_defaults_without_rewriting_invalid_toml(
    manager_and_config_dir: tuple[HandleConfigManager, Path],
) -> None:
    """Malformed TOML keeps the original file and returns defaults."""
    manager, config_dir = manager_and_config_dir
    config_file = config_dir / "kick_member.toml"
    invalid_content = "enabled = [\n"
    config_file.write_text(invalid_content, encoding="utf-8")

    config = await manager.get_config("kick_member")

    assert config.enabled is False
    assert config.defaults["require_reason"] is False
    assert config_file.read_text(encoding="utf-8") == invalid_content


@pytest.mark.asyncio
async def test_get_config_classifies_io_errors_without_raising(
    manager_and_config_dir: tuple[HandleConfigManager, Path],
) -> None:
    """Read I/O errors keep the compatible default-return behavior."""
    manager, config_dir = manager_and_config_dir
    config_file = config_dir / "kick_member.toml"
    config_file.write_text("enabled = false\n", encoding="utf-8")
    read_error = TOMLFileReadError(config_file, PermissionError("denied"))
    read_error.__cause__ = PermissionError("denied")

    with (
        patch.object(
            manager_module,
            "load_toml_dict_async",
            side_effect=read_error,
        ),
        patch.object(manager_module.logger, "error") as log_error,
    ):
        config = await manager.get_config("kick_member")

    assert config.enabled is False
    assert any(
        "I/O error reading handle config" in call.args[0]
        for call in log_error.call_args_list
    )


@pytest.mark.asyncio
async def test_update_config_does_not_overwrite_invalid_toml(
    manager_and_config_dir: tuple[HandleConfigManager, Path],
) -> None:
    """An invalid existing file blocks an update instead of being replaced."""
    manager, config_dir = manager_and_config_dir
    config_file = config_dir / "kick_member.toml"
    invalid_content = "enabled = [\n"
    config_file.write_text(invalid_content, encoding="utf-8")

    with pytest.raises(TOMLFileReadError):
        await manager.update_config("kick_member", {"enabled": False})

    assert config_file.read_text(encoding="utf-8") == invalid_content
