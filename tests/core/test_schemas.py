"""Tests for :mod:`core.schemas` localstore-backed schema installation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from _lingchu_bot_contracts import RuntimeSettings
import aiofiles
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import schemas as schemas_module
from src.plugins.nonebot_plugin_lingchu_bot.core.bot_state import BotStateFile
from src.plugins.nonebot_plugin_lingchu_bot.core.schemas import (
    BOT_STATE_SCHEMA_BASENAME,
    CONFIG_SCHEMA_BASENAME,
    MENU_SCHEMA_BASENAME,
    MENU_SCHEMA_TEXT,
    install_schemas,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def _config_schema_text() -> str:
    """Return the pydantic-generated CONFIG schema as a JSON string."""
    return json.dumps(RuntimeSettings.model_json_schema(), indent=2, ensure_ascii=False)


def _bot_state_schema_text() -> str:
    """Return the pydantic-generated BOT_STATE schema as a JSON string."""
    return json.dumps(BotStateFile.model_json_schema(), indent=2, ensure_ascii=False)


@pytest.fixture
def patched_localstore(
    tmp_path: Path,
) -> Iterator[tuple[Path, Path]]:
    """Redirect ``get_plugin_config_dir`` / ``get_plugin_data_dir`` to ``tmp_path``.

    Returns the (config_dir, data_dir) tuple so individual tests can assert
    the precise target paths.
    """
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    with (
        patch.object(
            schemas_module,
            "get_plugin_config_dir",
            return_value=config_dir,
        ),
        patch.object(
            schemas_module,
            "get_plugin_data_dir",
            return_value=data_dir,
        ),
    ):
        yield config_dir, data_dir


async def test_install_schemas_writes_config_schema_under_localstore_config_dir(
    patched_localstore: tuple[Path, Path],
) -> None:
    """``install_schemas`` writes the config schema to the localstore config dir."""
    config_dir, _ = patched_localstore

    await install_schemas()

    config_schema_path = config_dir / CONFIG_SCHEMA_BASENAME
    assert config_schema_path.exists()
    async with aiofiles.open(config_schema_path, encoding="utf-8") as f:
        assert await f.read() == _config_schema_text()


async def test_install_schemas_writes_bot_state_schema_under_localstore_data_dir(
    patched_localstore: tuple[Path, Path],
) -> None:
    """``install_schemas`` writes the bot state schema to the localstore data dir."""
    _, data_dir = patched_localstore

    await install_schemas()

    data_schema_path = data_dir / BOT_STATE_SCHEMA_BASENAME
    assert data_schema_path.exists()
    async with aiofiles.open(data_schema_path, encoding="utf-8") as f:
        assert await f.read() == _bot_state_schema_text()


async def test_install_schemas_writes_menu_schema_under_localstore_config_dir(
    patched_localstore: tuple[Path, Path],
) -> None:
    """``install_schemas`` writes the menu schema to the localstore config dir."""
    config_dir, _ = patched_localstore

    await install_schemas()

    menu_schema_path = config_dir / MENU_SCHEMA_BASENAME
    assert menu_schema_path.exists()
    async with aiofiles.open(menu_schema_path, encoding="utf-8") as f:
        assert await f.read() == MENU_SCHEMA_TEXT


async def test_install_schemas_uses_localstore_paths_only(
    patched_localstore: tuple[Path, Path],
) -> None:
    """Each schema is written under the corresponding localstore mock directory."""
    config_dir, data_dir = patched_localstore

    await install_schemas()

    # Both files exist only inside the mocked localstore directories.
    expected_config = config_dir / CONFIG_SCHEMA_BASENAME
    expected_menu = config_dir / MENU_SCHEMA_BASENAME
    expected_data = data_dir / BOT_STATE_SCHEMA_BASENAME
    assert expected_config.exists()
    assert expected_menu.exists()
    assert expected_data.exists()

    # The data schema is *not* placed under the config dir, and vice versa.
    assert not (config_dir / BOT_STATE_SCHEMA_BASENAME).exists()
    assert not (data_dir / CONFIG_SCHEMA_BASENAME).exists()
    assert not (data_dir / MENU_SCHEMA_BASENAME).exists()


async def test_install_schemas_is_idempotent(
    patched_localstore: tuple[Path, Path],
) -> None:
    """Repeated calls do not raise and leave the file contents unchanged."""
    config_dir, data_dir = patched_localstore

    await install_schemas()
    async with aiofiles.open(
        config_dir / CONFIG_SCHEMA_BASENAME, encoding="utf-8"
    ) as f:
        first_config = await f.read()
    async with aiofiles.open(config_dir / MENU_SCHEMA_BASENAME, encoding="utf-8") as f:
        first_menu = await f.read()
    async with aiofiles.open(
        data_dir / BOT_STATE_SCHEMA_BASENAME, encoding="utf-8"
    ) as f:
        first_data = await f.read()

    await install_schemas()

    async with aiofiles.open(
        config_dir / CONFIG_SCHEMA_BASENAME, encoding="utf-8"
    ) as f:
        assert await f.read() == first_config
    async with aiofiles.open(config_dir / MENU_SCHEMA_BASENAME, encoding="utf-8") as f:
        assert await f.read() == first_menu
    async with aiofiles.open(
        data_dir / BOT_STATE_SCHEMA_BASENAME, encoding="utf-8"
    ) as f:
        assert await f.read() == first_data


def test_menu_schema_text_is_valid_json() -> None:
    assert json.loads(MENU_SCHEMA_TEXT)["title"] == "Lingchu Bot Menu Config"


async def test_install_schemas_propagates_localstore_errors() -> None:
    """``install_schemas`` must not swallow localstore errors.

    The startup hook in ``start/startup.py`` wraps the call in
    ``try/except BLE001`` and logs via ``logger.exception`` without
    interrupting startup, but the schema module itself MUST let
    exceptions propagate so the double-layer failure contract is
    preserved (P6 in ``## Lessons Learned``). This test pins that
    contract by asserting a ``RuntimeError`` from localstore bubbles
    up unchanged.
    """
    with (
        patch.object(
            schemas_module,
            "get_plugin_config_dir",
            side_effect=RuntimeError("Cannot detect caller plugin"),
        ),
        pytest.raises(RuntimeError, match="Cannot detect caller plugin"),
    ):
        await install_schemas()
