"""Synchronous and asynchronous dictionary-file helpers for TOML."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import aiofiles.os
import rtoml

from ..persistence import (
    PersistenceJournal,
    append_checksum,
    atomic_write_text,
    compute_checksum,
    read_text,
    recover_file,
    verify_checksum,
    write_version,
)
from ._helpers import _deepcopy_async, _toml_dumps, _toml_dumps_async, _toml_loads_async
from .exceptions import (
    InvalidTOMLRootTypeError,
    TOMLFileReadError,
    TOMLSerializationError,
)


def _journal_for(path: Path) -> PersistenceJournal:
    """Return the persistence journal scoped to a file's directory."""
    return PersistenceJournal(path.parent)


def load_toml_dict_sync(
    file_path: str | Path,
    *,
    default: dict[str, Any] | None = None,
    merge_default: bool = False,
) -> dict[str, Any]:
    """Read a TOML table synchronously during import-time setup."""
    path = Path(file_path)
    default_copy = deepcopy(default) if default is not None else {}
    if not path.exists():
        return default_copy
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TOMLFileReadError(path, exc) from exc
    if not content.strip():
        return default_copy
    if not verify_checksum(content):
        # Corrupted file: try the crash-safe backup, else fall back to default.
        recovered = _recover_sync(path)
        if recovered is None:
            return default_copy
        content = recovered
    try:
        loaded: Any = rtoml.loads(content)
    except (OSError, ValueError) as exc:
        raise TOMLFileReadError(path, exc) from exc
    if not isinstance(loaded, dict):
        raise InvalidTOMLRootTypeError(path, type(loaded))
    return default_copy | loaded if merge_default else loaded


def _recover_sync(path: Path) -> str | None:
    """Synchronous recovery: quarantine corrupt file, restore intact backup."""
    import contextlib

    backup = path.with_name(f"{path.name}.bak")
    try:
        backup_content = backup.read_text(encoding="utf-8")
    except OSError:
        return None
    if not verify_checksum(backup_content):
        return None
    with contextlib.suppress(OSError):
        Path(path).replace(path.with_name(f"{path.name}.corrupt"))
    try:
        backup.replace(path)
    except OSError:
        return None
    return backup_content


async def load_toml_dict_async(
    file_path: str | Path,
    *,
    default: dict[str, Any] | None = None,
    merge_default: bool = False,
) -> dict[str, Any]:
    """Read a TOML table without blocking the event loop."""
    path = Path(file_path)
    default_copy = await _deepcopy_async(default if default is not None else {})
    if not await aiofiles.os.path.exists(path):
        return default_copy
    try:
        content = await read_text(path)
    except OSError as exc:
        raise TOMLFileReadError(path, exc) from exc
    if content is None or not content.strip():
        return default_copy
    if not verify_checksum(content):
        journal = _journal_for(path)
        recovered = await recover_file(path, journal)
        if recovered is None:
            await journal.record(
                "load_fallback", path, detail="corrupted file, using defaults"
            )
            return default_copy
        content = recovered
    try:
        loaded: Any = await _toml_loads_async(content)
    except (OSError, ValueError) as exc:
        raise TOMLFileReadError(path, exc) from exc
    if not isinstance(loaded, dict):
        raise InvalidTOMLRootTypeError(path, type(loaded))
    return default_copy | loaded if merge_default else loaded


def ensure_toml_dict_file_sync(
    file_path: str | Path,
    default: dict[str, Any],
    *,
    schema_basename: str | None = None,
) -> Path:
    # Sync I/O: import-time API; runtime uses ensure_toml_dict_file_async.
    path = Path(file_path)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        content = _toml_dumps(default, schema_basename=schema_basename)
        path.write_text(append_checksum(write_version(content)), encoding="utf-8")
    except TOMLSerializationError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise TOMLFileReadError(path, exc) from exc
    return path


async def ensure_toml_dict_file_async(
    file_path: str | Path,
    default: dict[str, Any],
    *,
    schema_basename: str | None = None,
) -> Path:
    path = Path(file_path)
    if await aiofiles.os.path.exists(path):
        return path
    content = await _toml_dumps_async(default, schema_basename=schema_basename)
    await _write_persisted(path, content)
    return path


async def write_toml_dict_file_async(
    file_path: str | Path,
    data: dict[str, Any],
    *,
    schema_basename: str | None = None,
) -> Path:
    path = Path(file_path)
    content = await _toml_dumps_async(data, schema_basename=schema_basename)
    await _write_persisted(path, content)
    return path


async def _write_persisted(path: Path, content: str) -> None:
    """Write TOML content with version + checksum, atomic replace, journal."""
    journal = _journal_for(path)
    try:
        # Checksum must cover the version line too, so verify on read matches.
        persisted = append_checksum(write_version(content))
        await atomic_write_text(path, persisted)
    except TOMLSerializationError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise TOMLFileReadError(path, exc) from exc
    await journal.record(
        "write",
        path,
        checksum=compute_checksum(content),
        detail="atomic write with backup",
    )
