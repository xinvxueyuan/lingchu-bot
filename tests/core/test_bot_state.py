"""Tests for :mod:`core.bot_state` TOML persistence."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import patch

import aiofiles
import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.core import bot_state as bot_state_module
from src.plugins.nonebot_plugin_lingchu_bot.core.bot_state import (
    BotStateFile,
    InvalidBotStateGlobalError,
    _save_bot_state,
    flush_bot_state_if_dirty,
    load_bot_state,
    set_global_handle_active,
    set_global_silent_mode,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import (
    TOMLFileReadError,
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


async def test_bot_state_default_contains_expected_payload(
    patched_state_dir: Path,
) -> None:
    """First-time load uses typed defaults without creating a data file."""
    bot_state_module._reset_state_for_testing()
    await load_bot_state()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    assert not state_file.exists()
    assert bot_state_module.get_global_handle_active() is True
    assert bot_state_module.get_global_silent_mode() is False
    assert bot_state_module.get_platform_handle_active("qq") is True
    assert bot_state_module.get_platform_silent_mode("qq") is False


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


@pytest.mark.parametrize(
    ("handle_active", "silent_mode"),
    [("false", 0), (None, "true")],
)
def test_bot_state_mapping_rejects_non_boolean_scalars(
    handle_active: object,
    silent_mode: object,
) -> None:
    model = BotStateFile.from_mapping({
        "global": {
            "handle_active": handle_active,
            "silent_mode": silent_mode,
        },
        "platforms": {
            "qq": {
                "handle_active": "false",
                "silent_mode": 1,
            }
        },
    })

    assert model.global_.handle_active is True
    assert model.global_.silent_mode is False
    assert model.platforms["qq"].handle_active is None
    assert model.platforms["qq"].silent_mode is None


async def test_bot_state_invalid_toml_uses_defaults_without_rewriting(
    patched_state_dir: Path,
) -> None:
    """Malformed TOML falls back in memory and leaves the file untouched."""
    bot_state_module._reset_state_for_testing()
    bot_state_module._state["global_handle_active"] = False
    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    invalid_content = "[global\nhandle_active = false\n"
    state_file.write_text(invalid_content, encoding="utf-8")

    await load_bot_state()

    assert bot_state_module.get_global_handle_active() is True
    assert state_file.read_text(encoding="utf-8") == invalid_content


async def test_bot_state_invalid_structure_fails_without_rewriting(
    patched_state_dir: Path,
) -> None:
    """Invalid state shape remains a startup error and is never repaired."""
    bot_state_module._reset_state_for_testing()
    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    invalid_content = "global = []\n"
    state_file.write_text(invalid_content, encoding="utf-8")

    with pytest.raises(InvalidBotStateGlobalError):
        await load_bot_state()

    assert state_file.read_text(encoding="utf-8") == invalid_content


async def test_bot_state_io_error_uses_defaults_without_rewriting(
    patched_state_dir: Path,
) -> None:
    """Read I/O failures fall back in memory and do not trigger a write."""
    bot_state_module._reset_state_for_testing()
    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    invalid_content = "global = {}\n"
    state_file.write_text(invalid_content, encoding="utf-8")
    read_error = TOMLFileReadError(state_file, PermissionError("denied"))
    read_error.__cause__ = PermissionError("denied")

    with (
        patch.object(
            bot_state_module,
            "load_toml_dict_async",
            side_effect=read_error,
        ),
        patch.object(bot_state_module.logger, "error") as log_error,
    ):
        await load_bot_state()

    assert bot_state_module.get_global_handle_active() is True
    assert state_file.read_text(encoding="utf-8") == invalid_content
    assert any(
        "I/O error reading bot state" in call.args[0]
        for call in log_error.call_args_list
    )


@pytest.mark.asyncio
async def test_bot_state_save_writes_expected_payload(
    patched_state_dir: Path,
) -> None:
    """Saving always regenerates the code-owned schema directive."""
    bot_state_module._reset_state_for_testing()

    await _save_bot_state()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    content = state_file.read_text(encoding="utf-8")
    assert "#:schema" not in content


@pytest.mark.asyncio
async def test_bot_state_flush_writes_only_when_state_changed(
    patched_state_dir: Path,
) -> None:
    bot_state_module._reset_state_for_testing()
    await load_bot_state()
    set_global_handle_active(active=False)

    first = await flush_bot_state_if_dirty()
    second = await flush_bot_state_if_dirty()

    state_file = patched_state_dir / bot_state_module._BOT_STATE_FILENAME
    assert first is True
    assert second is False
    assert state_file.exists()


@pytest.mark.asyncio
async def test_bot_state_flush_retries_when_state_changes_during_write(
    patched_state_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del patched_state_dir
    bot_state_module._reset_state_for_testing()
    await load_bot_state()
    set_global_handle_active(active=False)
    writes: list[dict[str, object]] = []

    async def write_state(_path: Path, state: dict[str, object]) -> None:
        writes.append(state)
        if len(writes) == 1:
            set_global_silent_mode(silent=True)
            await asyncio.sleep(0)

    monkeypatch.setattr(bot_state_module, "write_toml_dict_file_async", write_state)

    assert await flush_bot_state_if_dirty() is True
    assert [write["global"] for write in writes] == [
        {"handle_active": False, "silent_mode": False},
        {"handle_active": False, "silent_mode": True},
    ]
    assert bot_state_module._cache.dirty is False


@pytest.mark.asyncio
async def test_bot_state_flush_stops_after_retries_are_exhausted(
    patched_state_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del patched_state_dir
    bot_state_module._reset_state_for_testing()
    await load_bot_state()
    set_global_handle_active(active=False)
    writes = 0

    async def write_state(_path: Path, _state: dict[str, object]) -> None:
        nonlocal writes
        writes += 1
        set_global_silent_mode(silent=writes % 2 == 1)

    monkeypatch.setattr(bot_state_module, "write_toml_dict_file_async", write_state)

    assert await flush_bot_state_if_dirty() is True
    assert writes == 3
    assert bot_state_module._cache.dirty is True
