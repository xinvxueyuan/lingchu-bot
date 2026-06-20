"""Tests for ``ensure_json5_dict_file_async``.

Mirrors the behaviour of ``ensure_json5_dict_file_sync`` but exercises the
``aiofiles``-backed async implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import json5
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.json5_store import (
    JSON5FileReadError,
    ensure_json5_dict_file_async,
)

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_PAYLOAD: dict[str, Any] = {"message_store_enabled": True, "count": 42}


@pytest.mark.asyncio
async def test_ensure_async_creates_file_when_missing(tmp_path: Path) -> None:
    config_file = tmp_path / "nested" / "config.json5"

    created = await ensure_json5_dict_file_async(config_file, DEFAULT_PAYLOAD)

    assert created == config_file
    assert config_file.exists()
    loaded = json5.loads(config_file.read_text(encoding="utf-8"))
    assert loaded == DEFAULT_PAYLOAD


@pytest.mark.asyncio
async def test_ensure_async_preserves_existing_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"
    config_file.write_text("{message_store_retention_days: 7}", encoding="utf-8")
    original_mtime = config_file.stat().st_mtime_ns

    created = await ensure_json5_dict_file_async(config_file, DEFAULT_PAYLOAD)

    assert created == config_file
    assert "7" in config_file.read_text(encoding="utf-8")
    assert config_file.stat().st_mtime_ns == original_mtime


@pytest.mark.asyncio
async def test_ensure_async_writes_valid_json5(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"

    await ensure_json5_dict_file_async(config_file, DEFAULT_PAYLOAD)

    content = config_file.read_text(encoding="utf-8")
    parsed = json5.loads(content)
    assert parsed == DEFAULT_PAYLOAD
    assert isinstance(parsed, dict)


@pytest.mark.asyncio
async def test_ensure_async_does_not_leave_temp_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"

    await ensure_json5_dict_file_async(config_file, DEFAULT_PAYLOAD)

    temp_path = config_file.with_suffix(".tmp.json5")
    assert not temp_path.exists()


@pytest.mark.asyncio
async def test_ensure_async_raises_on_unserializable_default(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json5"
    bad_payload: dict[str, Any] = {"broken": object()}

    with pytest.raises(JSON5FileReadError):
        await ensure_json5_dict_file_async(config_file, bad_payload)

    assert not config_file.exists()
    assert not config_file.with_suffix(".tmp.json5").exists()
