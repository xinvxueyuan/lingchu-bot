"""Synchronous and asynchronous dictionary-file helpers for TOML."""

from __future__ import annotations

import asyncio
import contextlib
from copy import deepcopy
import os
from pathlib import Path
import tempfile
from typing import Any

import aiofiles
import aiofiles.os
import rtoml

from ._helpers import _deepcopy_async, _toml_dumps, _toml_dumps_async, _toml_loads_async
from .exceptions import (
    InvalidTOMLRootTypeError,
    TOMLFileReadError,
    TOMLSerializationError,
)

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_POLL_SECONDS = 0.05


def _lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


async def _acquire_file_lock(path: Path) -> int:
    lock_path = _lock_path(path)
    deadline = asyncio.get_running_loop().time() + _LOCK_TIMEOUT_SECONDS
    while True:
        try:
            return await asyncio.to_thread(
                os.open,
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError as exc:
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError from exc
            await asyncio.sleep(_LOCK_POLL_SECONDS)


async def _release_file_lock(path: Path, fd: int) -> None:
    await asyncio.to_thread(os.close, fd)
    with contextlib.suppress(OSError):
        await aiofiles.os.unlink(_lock_path(path))


async def _fsync_path(path: Path) -> None:
    """Flush a file and its parent directory where the platform supports it."""
    with contextlib.suppress(OSError):
        directory_fd = await asyncio.to_thread(os.open, path.parent, os.O_RDONLY)
        try:
            await asyncio.to_thread(os.fsync, directory_fd)
        finally:
            await asyncio.to_thread(os.close, directory_fd)


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
        loaded: Any = rtoml.loads(content) if content.strip() else default_copy
    except (OSError, ValueError) as exc:
        raise TOMLFileReadError(path, exc) from exc
    if not isinstance(loaded, dict):
        raise InvalidTOMLRootTypeError(path, type(loaded))
    return default_copy | loaded if merge_default else loaded


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
        async with aiofiles.open(path, encoding="utf-8") as file:
            content = await file.read()
        loaded: Any = (
            await _toml_loads_async(content) if content.strip() else default_copy
        )
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
    temp_path: Path | None = None
    try:
        content = _toml_dumps(default, schema_basename=schema_basename)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(path)
    except TOMLSerializationError:
        with contextlib.suppress(OSError):
            if temp_path is not None:
                temp_path.unlink()
        raise
    except (OSError, TypeError, ValueError) as exc:
        with contextlib.suppress(OSError):
            if temp_path is not None:
                temp_path.unlink()
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
    await aiofiles.os.makedirs(path.parent, exist_ok=True)
    temp_path: Path | None = None
    lock_fd = await _acquire_file_lock(path)
    try:
        content = await _toml_dumps_async(default, schema_basename=schema_basename)
        fd, temp_name = await asyncio.to_thread(
            tempfile.mkstemp,
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temp_path = Path(os.fsdecode(temp_name))
        async with aiofiles.open(fd, "w", encoding="utf-8") as file:
            await file.write(content)
            await file.flush()
            await asyncio.to_thread(os.fsync, file.fileno())
        await aiofiles.os.replace(temp_path, path)
        await _fsync_path(path)
    except TOMLSerializationError:
        with contextlib.suppress(OSError):
            if temp_path is not None:
                await aiofiles.os.unlink(temp_path)
        raise
    except (OSError, TypeError, ValueError) as exc:
        with contextlib.suppress(OSError):
            if temp_path is not None:
                await aiofiles.os.unlink(temp_path)
        raise TOMLFileReadError(path, exc) from exc
    finally:
        await _release_file_lock(path, lock_fd)
    return path


async def write_toml_dict_file_async(
    file_path: str | Path,
    data: dict[str, Any],
    *,
    schema_basename: str | None = None,
) -> Path:
    path = Path(file_path)
    await aiofiles.os.makedirs(path.parent, exist_ok=True)
    temp_path: Path | None = None
    lock_fd = await _acquire_file_lock(path)
    try:
        content = await _toml_dumps_async(data, schema_basename=schema_basename)
        fd, temp_name = await asyncio.to_thread(
            tempfile.mkstemp,
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temp_path = Path(os.fsdecode(temp_name))
        async with aiofiles.open(fd, "w", encoding="utf-8") as file:
            await file.write(content)
            await file.flush()
            await asyncio.to_thread(os.fsync, file.fileno())
        await aiofiles.os.replace(temp_path, path)
        await _fsync_path(path)
    except TOMLSerializationError:
        with contextlib.suppress(OSError):
            if temp_path is not None:
                await aiofiles.os.unlink(temp_path)
        raise
    except (OSError, TypeError, ValueError) as exc:
        with contextlib.suppress(OSError):
            if temp_path is not None:
                await aiofiles.os.unlink(temp_path)
        raise TOMLFileReadError(path, exc) from exc
    finally:
        await _release_file_lock(path, lock_fd)
    return path
