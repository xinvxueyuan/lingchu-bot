"""Tests for :mod:`core.bot_state` JSON5 persistence and ``$schema`` handling."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import json5
import pytest

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


def test_bot_state_default_contains_schema(
    patched_state_dir: Path,  # type: ignore[ANN001]
) -> None:  # type: ignore[ANN001]
    """First-time load writes a default file with a ``$schema`` basename."""
    bot_state_module._reset_state_for_testing()
    load_bot_state()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    assert state_file.exists()
    payload = json5.loads(state_file.read_text(encoding="utf-8"))
    assert payload["$schema"] == bot_state_module.BOT_STATE_SCHEMA_BASENAME
    assert payload["global"]["handle_active"] is True
    assert payload["global"]["silent_mode"] is False
    assert payload["platforms"] == {}


def test_bot_state_existing_file_preserves_user_state(
    patched_state_dir: Path,  # type: ignore[ANN001]
) -> None:
    """An existing ``bot_state.json5`` without ``$schema`` still loads."""
    bot_state_module._reset_state_for_testing()
    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    state_file.write_text(
        json5.dumps(
            {
                "global": {
                    "handle_active": False,
                    "silent_mode": True,
                },
                "platforms": {"qq": {"handle_active": False}},
            }
        ),
        encoding="utf-8",
    )

    load_bot_state()

    assert bot_state_module.get_global_handle_active() is False
    assert bot_state_module.get_global_silent_mode() is True
    assert bot_state_module.is_handle_active("qq") is False
    assert bot_state_module.is_silent_mode("qq") is True


@pytest.mark.asyncio
async def test_bot_state_save_preserves_user_schema(
    patched_state_dir: Path,  # type: ignore[ANN001]
) -> None:
    """Saving a state with a custom ``$schema`` keeps the user value."""
    bot_state_module._reset_state_for_testing()
    bot_state_module._state["$schema"] = "custom-bot-state.schema.json5"

    await _save_bot_state()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    payload = json5.loads(state_file.read_text(encoding="utf-8"))
    assert payload["$schema"] == "custom-bot-state.schema.json5"


@pytest.mark.asyncio
async def test_bot_state_save_falls_back_to_default_basename(
    patched_state_dir,  # noqa: ANN001
) -> None:
    """Saving without a cached ``$schema`` falls back to the default basename."""
    bot_state_module._reset_state_for_testing()
    bot_state_module._state["$schema"] = None

    await _save_bot_state()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    payload = json5.loads(state_file.read_text(encoding="utf-8"))
    assert payload["$schema"] == bot_state_module.BOT_STATE_SCHEMA_BASENAME
