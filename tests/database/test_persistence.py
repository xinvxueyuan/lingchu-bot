"""Tests for the unified persistence layer (integrity/atomicity/recovery)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.persistence import (
    PersistenceJournal,
    append_checksum,
    atomic as atomic_mod,
    atomic_write_text,
    backup_path,
    cleanup_stale_temp_files,
    compute_checksum,
    current_version,
    extract_checksum,
    migrate_content,
    quarantine_corrupt,
    read_text,
    read_version,
    recover_file,
    verify_checksum,
    verify_file,
    versioning as versioning_mod,
    write_version,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import (
    ensure_toml_dict_file_sync,
    load_toml_dict_async,
    load_toml_dict_sync,
    write_toml_dict_file_async,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store._sync import (
    _recover_sync,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store.exceptions import (
    InvalidTOMLRootTypeError,
    TOMLFileReadError,
    TOMLSerializationError,
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


# ---------------------------------------------------------------------------
# edge cases: checksum / versioning
# ---------------------------------------------------------------------------


def test_extract_checksum_empty_content() -> None:
    body, stored = extract_checksum("")
    assert body == ""
    assert stored is None


def test_current_version() -> None:
    assert current_version() == 1


def test_read_version_invalid_value_returns_one() -> None:
    assert read_version("# lingchu-version: abc\n") == 1


def test_read_version_ignores_version_after_content() -> None:
    # A version line after real content is not the format header.
    assert read_version("a = 1\n# lingchu-version: 5\n") == 1


def test_read_version_comment_only_content() -> None:
    # Comment-only content never matches the version header and stays at 1.
    assert read_version("# c1\n# c2\n") == 1


def test_migrate_content_runs_registered_migrations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def migrate_v0(content: str) -> str:
        return content + "migrated = true\n"

    monkeypatch.setitem(versioning_mod.MIGRATIONS, 0, migrate_v0)
    result = migrate_content("# lingchu-version: 0\nold = 1\n")

    assert "migrated = true" in result
    assert result.startswith("# lingchu-version: 1")


def test_migrate_content_skips_missing_migration() -> None:
    # No migration registered for version 0: content passes through unchanged.
    result = migrate_content("# lingchu-version: 0\nold = 1\n")

    assert result.startswith("# lingchu-version: 1")
    assert "old = 1" in result


# ---------------------------------------------------------------------------
# edge cases: atomic write / read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_write_lock_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.toml"
    lock = tmp_path / ".state.toml.lock"
    lock.write_text("held by another process")
    monkeypatch.setattr(atomic_mod, "_LOCK_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(atomic_mod, "_LOCK_POLL_SECONDS", 0.01)

    with pytest.raises(TimeoutError):
        await atomic_write_text(target, "v1\n")


@pytest.mark.asyncio
async def test_fsync_path_flushes_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, int]] = []
    real_open = os.open
    subdir = tmp_path / "sub"
    subdir.mkdir()

    def fake_open(path: str | os.PathLike[str], flags: int, *args: Any) -> int:
        if Path(path) == tmp_path:
            return 123
        return real_open(path, flags, *args)

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fsync", lambda fd: calls.append(("fsync", fd)))
    monkeypatch.setattr(os, "close", lambda fd: calls.append(("close", fd)))

    await atomic_mod._fsync_path(subdir)

    assert ("fsync", 123) in calls
    assert ("close", 123) in calls


@pytest.mark.asyncio
async def test_copy_file_oserror_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src.toml"
    dst = tmp_path / "dst.toml"
    src.write_text("data")

    async def boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("boom")

    monkeypatch.setattr(atomic_mod.aiofiles.os, "replace", boom)

    with pytest.raises(OSError):
        await atomic_mod._copy_file(src, dst)

    entries = await aiofiles.os.listdir(tmp_path)
    leftovers = [entry for entry in entries if entry.endswith(".tmp")]
    assert leftovers == []


@pytest.mark.asyncio
async def test_atomic_write_oserror_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.toml"

    async def boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("boom")

    monkeypatch.setattr(atomic_mod.aiofiles.os, "replace", boom)

    with pytest.raises(OSError):
        await atomic_write_text(target, "v1\n")

    entries = await aiofiles.os.listdir(tmp_path)
    leftovers = [entry for entry in entries if entry.endswith(".tmp")]
    assert leftovers == []


@pytest.mark.asyncio
async def test_cleanup_stale_temp_files_non_directory(tmp_path: Path) -> None:
    plain = tmp_path / "plain.txt"
    plain.write_text("x")

    assert await cleanup_stale_temp_files(plain) == 0


@pytest.mark.asyncio
async def test_read_text_oserror_returns_none(tmp_path: Path) -> None:
    # Reading a directory raises IsADirectoryError (an OSError subclass).
    assert await read_text(tmp_path) is None


# ---------------------------------------------------------------------------
# edge cases: recovery / journal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_file_missing_returns_true(tmp_path: Path) -> None:
    assert await verify_file(tmp_path / "missing.toml") is True


@pytest.mark.asyncio
async def test_quarantine_corrupt_moves_file(tmp_path: Path) -> None:
    target = tmp_path / "state.toml"
    target.write_text("corrupt")

    await quarantine_corrupt(target)

    assert not target.exists()
    assert (tmp_path / "state.toml.corrupt").exists()


@pytest.mark.asyncio
async def test_journal_record_oserror_is_silent(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    journal = PersistenceJournal(blocker / "sub")

    # makedirs fails because the parent is a file; journaling must not raise.
    await journal.record("write", tmp_path / "state.toml")


# ---------------------------------------------------------------------------
# edge cases: toml_store sync path
# ---------------------------------------------------------------------------


def test_load_toml_dict_sync_oserror(tmp_path: Path) -> None:
    with pytest.raises(TOMLFileReadError):
        load_toml_dict_sync(tmp_path)  # directory -> IsADirectoryError


def test_load_toml_dict_sync_recovers_from_backup(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    persisted = append_checksum(write_version("value = 1\n"))
    target.write_text(persisted, encoding="utf-8")
    backup_path(target).write_text(persisted, encoding="utf-8")
    # Tamper with the body but keep the original checksum line.
    target.write_text(persisted.replace("value = 1", "value = 999"), encoding="utf-8")

    loaded = load_toml_dict_sync(target)

    assert loaded == {"value": 1}


def test_load_toml_dict_sync_falls_back_when_no_backup(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    persisted = append_checksum(write_version("value = 1\n"))
    target.write_text(persisted.replace("value = 1", "value = 999"), encoding="utf-8")

    loaded = load_toml_dict_sync(target, default={"fallback": True})

    assert loaded == {"fallback": True}


def test_recover_sync_missing_backup_returns_none(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("corrupt", encoding="utf-8")

    assert _recover_sync(target) is None


def test_load_toml_dict_sync_invalid_toml(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("not = [valid\n", encoding="utf-8")

    with pytest.raises(TOMLFileReadError):
        load_toml_dict_sync(target)


def test_load_toml_dict_sync_invalid_root_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "config.toml"
    target.write_text("a = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.database.toml_store._sync.rtoml.loads",
        lambda *_: [1, 2],
    )

    with pytest.raises(InvalidTOMLRootTypeError):
        load_toml_dict_sync(target)


def test_recover_sync_no_intact_backup(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text(append_checksum("value = 999\n"), encoding="utf-8")
    # Backup exists but its checksum does not match its body.
    backup_path(target).write_text(
        append_checksum("value = 1\n").replace("value = 1", "value = 2"),
        encoding="utf-8",
    )

    assert _recover_sync(target) is None


# ---------------------------------------------------------------------------
# edge cases: toml_store async path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_toml_dict_async_invalid_root_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "config.toml"
    target.write_text("a = 1\n", encoding="utf-8")

    async def fake_loads(_content: str) -> list[int]:
        return [1, 2]

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.database.toml_store._sync._toml_loads_async",
        fake_loads,
    )

    with pytest.raises(InvalidTOMLRootTypeError):
        await load_toml_dict_async(target)


def test_ensure_toml_dict_file_sync_exists(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("existing = true\n", encoding="utf-8")

    result = ensure_toml_dict_file_sync(target, {"value": 1})

    assert result == target
    assert target.read_text(encoding="utf-8") == "existing = true\n"


def test_ensure_toml_dict_file_sync_serialization_error(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"

    with pytest.raises(TOMLSerializationError):
        ensure_toml_dict_file_sync(target, {"bad": [None]})


@pytest.mark.asyncio
async def test_write_persisted_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "config.toml"

    async def boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("boom")

    monkeypatch.setattr(atomic_mod.aiofiles.os, "replace", boom)

    with pytest.raises(TOMLFileReadError):
        await write_toml_dict_file_async(target, {"value": 1})
