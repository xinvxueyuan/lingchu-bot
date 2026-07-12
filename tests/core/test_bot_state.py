"""Tests for :mod:`core.bot_state` TOML persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import aiofiles
import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.core import bot_state as bot_state_module
from src.plugins.nonebot_plugin_lingchu_bot.core.bot_state import (
    _save_bot_state,
    load_bot_state,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def patched_state_dir(tmp_path: Path) -> Iterator[Path]:
    """Redirect ``get_plugin_data_file`` to a fresh ``tmp_path`` directory.

    Mirrors the real ``nonebot_plugin_localstore`` semantics:
    ``get_plugin_data_file(filename) == get_plugin_data_dir() / filename``.
    """
    target = tmp_path / "data"
    target.mkdir(parents=True, exist_ok=True)
    with patch.object(
        bot_state_module,
        "get_plugin_data_file",
        side_effect=lambda filename: target / filename,
    ):
        yield target


async def test_bot_state_default_contains_schema_directive(
    patched_state_dir: Path,
) -> None:
    """First-time load writes a schema directive outside the data table."""
    bot_state_module._reset_state_for_testing()
    await load_bot_state()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    assert state_file.exists()
    content = state_file.read_text(encoding="utf-8")
    payload = rtoml.loads(content)
    assert content.startswith(
        f"#:schema ./{bot_state_module.BOT_STATE_SCHEMA_BASENAME}\n"
    )
    assert "$schema" not in payload
    assert payload["global"]["handle_active"] is True
    assert payload["global"]["silent_mode"] is False
    assert payload["platforms"] == {}


async def test_bot_state_existing_file_preserves_user_state(
    patched_state_dir: Path,
) -> None:
    """An existing ``bot_state.toml`` without ``$schema`` still loads."""
    bot_state_module._reset_state_for_testing()
    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    async with aiofiles.open(state_file, "w", encoding="utf-8") as f:
        await f.write(
            rtoml.dumps({
                "global": {
                    "handle_active": False,
                    "silent_mode": True,
                },
                "platforms": {"qq": {"handle_active": False}},
            })
        )

    await load_bot_state()

    assert bot_state_module.get_global_handle_active() is False
    assert bot_state_module.get_global_silent_mode() is True
    assert bot_state_module.is_handle_active("qq") is False
    assert bot_state_module.is_silent_mode("qq") is True


@pytest.mark.asyncio
async def test_bot_state_save_writes_default_schema_directive(
    patched_state_dir: Path,
) -> None:
    """Saving always regenerates the code-owned schema directive."""
    bot_state_module._reset_state_for_testing()

    await _save_bot_state()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    content = state_file.read_text(encoding="utf-8")
    assert content.startswith(
        f"#:schema ./{bot_state_module.BOT_STATE_SCHEMA_BASENAME}\n"
    )
