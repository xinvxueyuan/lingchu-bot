"""Tests for ``ensure_toml_dict_file_async``.

Mirrors the behaviour of ``ensure_toml_dict_file_sync`` but exercises the
``aiofiles``-backed async implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiofiles
import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import (
    TOMLSerializationError,
    ensure_toml_dict_file_async,
    ensure_toml_dict_file_sync,
    write_toml_dict_file_async,
)

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_PAYLOAD: dict[str, Any] = {"message_store_enabled": True, "count": 42}


def test_ensure_sync_does_not_follow_predictable_temp_symlink(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("protected", encoding="utf-8")
    config_file.with_suffix(".tmp.toml").symlink_to(outside_file)

    ensure_toml_dict_file_sync(config_file, DEFAULT_PAYLOAD)

    assert outside_file.read_text(encoding="utf-8") == "protected"
    assert rtoml.loads(config_file.read_text(encoding="utf-8")) == DEFAULT_PAYLOAD


@pytest.mark.asyncio
async def test_ensure_async_creates_file_when_missing(tmp_path: Path) -> None:
    config_file = tmp_path / "nested" / "config.toml"

    created = await ensure_toml_dict_file_async(config_file, DEFAULT_PAYLOAD)

    assert created == config_file
    assert config_file.exists()
    async with aiofiles.open(config_file, encoding="utf-8") as f:
        loaded = rtoml.loads(await f.read())
    assert loaded == DEFAULT_PAYLOAD


@pytest.mark.asyncio
async def test_ensure_async_preserves_existing_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("message_store_retention_days = 7\n")
    original_mtime = config_file.stat().st_mtime_ns

    created = await ensure_toml_dict_file_async(config_file, DEFAULT_PAYLOAD)

    assert created == config_file
    async with aiofiles.open(config_file, encoding="utf-8") as f:
        assert "7" in await f.read()
    assert config_file.stat().st_mtime_ns == original_mtime


@pytest.mark.asyncio
async def test_ensure_async_writes_valid_toml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"

    await ensure_toml_dict_file_async(config_file, DEFAULT_PAYLOAD)

    async with aiofiles.open(config_file, encoding="utf-8") as f:
        content = await f.read()
    parsed = rtoml.loads(content)
    assert parsed == DEFAULT_PAYLOAD
    assert isinstance(parsed, dict)


@pytest.mark.asyncio
async def test_ensure_async_does_not_leave_temp_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"

    await ensure_toml_dict_file_async(config_file, DEFAULT_PAYLOAD)

    temp_path = config_file.with_suffix(".tmp.toml")
    assert not temp_path.exists()


@pytest.mark.asyncio
async def test_ensure_async_raises_on_unserializable_default(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    bad_payload: dict[str, Any] = {"broken": object()}

    with pytest.raises(TOMLSerializationError):
        await ensure_toml_dict_file_async(config_file, bad_payload)

    assert not config_file.exists()
    assert not config_file.with_suffix(".tmp.toml").exists()


@pytest.mark.asyncio
async def test_ensure_async_does_not_follow_predictable_temp_symlink(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("protected", encoding="utf-8")
    config_file.with_suffix(".tmp.toml").symlink_to(outside_file)

    await ensure_toml_dict_file_async(config_file, DEFAULT_PAYLOAD)

    assert outside_file.read_text(encoding="utf-8") == "protected"
    assert rtoml.loads(config_file.read_text(encoding="utf-8")) == DEFAULT_PAYLOAD


@pytest.mark.asyncio
async def test_write_async_does_not_follow_predictable_temp_symlink(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("protected", encoding="utf-8")
    config_file.with_suffix(".tmp.toml").symlink_to(outside_file)

    await write_toml_dict_file_async(config_file, DEFAULT_PAYLOAD)

    assert outside_file.read_text(encoding="utf-8") == "protected"
    assert rtoml.loads(config_file.read_text(encoding="utf-8")) == DEFAULT_PAYLOAD
