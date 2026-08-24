"""Tests for the unified persistence layer (integrity/atomicity/recovery)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.persistence import (
    PersistenceJournal,
    append_checksum,
    atomic_write_text,
    backup_path,
    cleanup_stale_temp_files,
    compute_checksum,
    extract_checksum,
    migrate_content,
    read_text,
    read_version,
    recover_file,
    verify_checksum,
    verify_file,
    write_version,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import (
    load_toml_dict_async,
    write_toml_dict_file_async,
)

# ---------------------------------------------------------------------------
# checksum
# ---------------------------------------------------------------------------


def test_append_and_verify_checksum_round_trip() -> None:
    content = "a = 1\nb = 2\n"
    persisted = append_checksum(content)

    assert verify_checksum(persisted) is True
    body, stored = extract_checksum(persisted)
    assert body == content.rstrip()
    assert stored == compute_checksum(content.rstrip())


def test_verify_checksum_detects_tampering() -> None:
    persisted = append_checksum("a = 1\n")
    tampered = persisted.replace("a = 1", "a = 999")

    assert verify_checksum(tampered) is False


def test_verify_checksum_accepts_legacy_content_without_checksum() -> None:
    # Files written before the checksum feature carry no checksum line.
    assert verify_checksum("a = 1\n") is True


def test_extract_checksum_returns_none_for_legacy() -> None:
    body, stored = extract_checksum("a = 1\n")
    assert stored is None
    assert body == "a = 1\n"


# ---------------------------------------------------------------------------
# versioning
# ---------------------------------------------------------------------------


def test_write_and_read_version() -> None:
    content = write_version("a = 1\n")
    assert read_version(content) == 1
    assert content.startswith("# lingchu-version: 1")


def test_read_version_defaults_to_one_for_legacy() -> None:
    assert read_version("a = 1\n") == 1
    assert read_version("") == 1


def test_migrate_content_noop_when_current() -> None:
    content = write_version("a = 1\n")
    assert migrate_content(content) == content


# ---------------------------------------------------------------------------
# atomic write + backup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_write_creates_file_and_backup(tmp_path: Path) -> None:
    target = tmp_path / "state.toml"
    await atomic_write_text(target, "v1\n")
    await atomic_write_text(target, "v2\n")

    assert await read_text(target) == "v2\n"
    assert await read_text(backup_path(target)) == "v1\n"


@pytest.mark.asyncio
async def test_atomic_write_first_write_has_no_backup(tmp_path: Path) -> None:
    target = tmp_path / "fresh.toml"
    await atomic_write_text(target, "v1\n")

    assert await read_text(target) == "v1\n"
    assert not await aiofiles.os.path.exists(backup_path(target))


@pytest.mark.asyncio
async def test_cleanup_stale_temp_files(tmp_path: Path) -> None:
    stale = tmp_path / ".state.toml.abc123.tmp"
    async with aiofiles.open(stale, "w") as f:
        await f.write("partial")
    keep = tmp_path / "state.toml"
    async with aiofiles.open(keep, "w") as f:
        await f.write("ok")

    removed = await cleanup_stale_temp_files(tmp_path)

    assert removed == 1
    assert not await aiofiles.os.path.exists(stale)
    assert await aiofiles.os.path.exists(keep)


# ---------------------------------------------------------------------------
# recovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recover_file_restores_intact_backup(tmp_path: Path) -> None:
    target = tmp_path / "state.toml"
    await atomic_write_text(target, append_checksum("value = 1\n"))
    await atomic_write_text(target, append_checksum("value = 2\n"))
    # Corrupt the current file (tamper with the body).
    corrupted = (await read_text(target) or "").replace("value = 2", "value = 999")
    async with aiofiles.open(target, "w") as f:
        await f.write(corrupted)
    journal = PersistenceJournal(tmp_path)

    recovered = await recover_file(target, journal)

    assert recovered is not None
    assert verify_checksum(recovered) is True
    # The backup is the pre-write snapshot of the last successful write.
    assert "value = 1" in recovered
    # The corrupted file is quarantined for forensics.
    assert await aiofiles.os.path.exists(tmp_path / "state.toml.corrupt")


@pytest.mark.asyncio
async def test_recover_file_returns_none_without_backup(tmp_path: Path) -> None:
    target = tmp_path / "state.toml"
    # A first write produces no backup; corrupting it leaves nothing to restore.
    await atomic_write_text(target, append_checksum("value = 1\n"))
    corrupted = (await read_text(target) or "").replace("value = 1", "value = 999")
    async with aiofiles.open(target, "w") as f:
        await f.write(corrupted)
    journal = PersistenceJournal(tmp_path)

    recovered = await recover_file(target, journal)

    assert recovered is None


@pytest.mark.asyncio
async def test_verify_file_detects_corruption(tmp_path: Path) -> None:
    target = tmp_path / "state.toml"
    await atomic_write_text(target, append_checksum("value = 1\n"))

    assert await verify_file(target) is True
    corrupted = (await read_text(target) or "").replace("value = 1", "value = 999")
    async with aiofiles.open(target, "w") as f:
        await f.write(corrupted)
    assert await verify_file(target) is False


# ---------------------------------------------------------------------------
# journal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_journal_records_and_reads_entries(tmp_path: Path) -> None:
    journal = PersistenceJournal(tmp_path)
    target = tmp_path / "state.toml"

    await journal.record("write", target, checksum="abc", detail="atomic write")
    await journal.record("recovered", target, detail="restored from backup")

    entries = await journal.read_entries()
    assert len(entries) == 2
    assert "write" in entries[0]
    assert "abc" in entries[0]
    assert "recovered" in entries[1]


@pytest.mark.asyncio
async def test_journal_missing_file_returns_empty(tmp_path: Path) -> None:
    journal = PersistenceJournal(tmp_path / "missing")
    assert await journal.read_entries() == []


# ---------------------------------------------------------------------------
# integration: toml_store write/load with integrity + recovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_load_round_trip_with_checksum(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    payload: dict[str, Any] = {"enabled": True, "count": 7}

    await write_toml_dict_file_async(target, payload)
    loaded = await load_toml_dict_async(target)

    assert loaded == payload
    content = await read_text(target)
    assert content is not None
    assert verify_checksum(content) is True
    assert "# lingchu-version: 1" in content


@pytest.mark.asyncio
async def test_load_recovers_corrupted_file_from_backup(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    await write_toml_dict_file_async(target, {"value": 1})
    await write_toml_dict_file_async(target, {"value": 2})
    # Tamper with the current file body.
    corrupted = (await read_text(target) or "").replace("value = 2", "value = 999")
    async with aiofiles.open(target, "w") as f:
        await f.write(corrupted)

    loaded = await load_toml_dict_async(target)

    # Recovery restores the pre-write backup (value=1, last successful state).
    assert loaded == {"value": 1}


@pytest.mark.asyncio
async def test_load_falls_back_to_default_when_no_backup(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    # First write has no backup; corrupting it leaves nothing to restore.
    await write_toml_dict_file_async(target, {"value": 1})
    corrupted = (await read_text(target) or "").replace("value = 1", "value = 999")
    async with aiofiles.open(target, "w") as f:
        await f.write(corrupted)

    loaded = await load_toml_dict_async(target, default={"fallback": True})

    assert loaded == {"fallback": True}


@pytest.mark.asyncio
async def test_load_accepts_legacy_file_without_checksum(tmp_path: Path) -> None:
    target = tmp_path / "legacy.toml"
    async with aiofiles.open(target, "w") as f:
        await f.write("legacy = true\n")

    loaded = await load_toml_dict_async(target)

    assert loaded == {"legacy": True}
