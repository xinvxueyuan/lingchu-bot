"""Atomic file writes with crash-safe backup.

Writes go through a temp file + fsync + rename so a crash or power loss
never leaves a partially-written target file. Before overwriting an existing
file, a backup copy (``<name>.bak``) is created so a corrupted write can be
rolled back on the next read.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from pathlib import Path
import tempfile

import aiofiles
import aiofiles.os

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_POLL_SECONDS = 0.05


def backup_path(path: Path) -> Path:
    """Return the backup path for a persisted file."""
    return path.with_name(f"{path.name}.bak")


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


async def _copy_file(src: Path, dst: Path) -> None:
    """Copy src to dst via a temp file + rename (crash-safe backup)."""
    fd, temp_name = await asyncio.to_thread(
        tempfile.mkstemp,
        prefix=f".{dst.name}.",
        suffix=".tmp",
        dir=dst.parent,
    )
    temp_path = Path(os.fsdecode(temp_name))
    try:
        async with (
            aiofiles.open(src, "rb") as reader,
            aiofiles.open(fd, "wb") as writer,
        ):
            while chunk := await reader.read(64 * 1024):
                await writer.write(chunk)
            await writer.flush()
            await asyncio.to_thread(os.fsync, writer.fileno())
        await aiofiles.os.replace(temp_path, dst)
        await _fsync_path(dst)
    except OSError:
        with contextlib.suppress(OSError):
            await aiofiles.os.unlink(temp_path)
        raise


async def atomic_write_text(path: Path, content: str) -> Path:
    """Atomically write text content to ``path`` with a pre-write backup.

    The existing file (if any) is copied to ``<name>.bak`` before the new
    content replaces the target, so a failed or corrupted write can be rolled
    back. Returns the target path.
    """
    await aiofiles.os.makedirs(path.parent, exist_ok=True)
    lock_fd = await _acquire_file_lock(path)
    temp_path: Path | None = None
    try:
        if await aiofiles.os.path.exists(path):
            await _copy_file(path, backup_path(path))
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
    except OSError:
        with contextlib.suppress(OSError):
            if temp_path is not None:
                await aiofiles.os.unlink(temp_path)
        raise
    finally:
        await _release_file_lock(path, lock_fd)
    return path


async def cleanup_stale_temp_files(directory: Path) -> int:
    """Remove leftover ``.<name>.*.tmp`` files from interrupted writes.

    Returns the number of files removed. Safe to call at startup.
    """
    if not await aiofiles.os.path.isdir(directory):
        return 0
    removed = 0
    for entry in await aiofiles.os.listdir(directory):
        if entry.endswith(".tmp") and entry.startswith("."):
            with contextlib.suppress(OSError):
                await aiofiles.os.unlink(directory / entry)
                removed += 1
    return removed


async def read_text(path: Path) -> str | None:
    """Read file text, returning None when the file does not exist."""
    try:
        async with aiofiles.open(path, encoding="utf-8") as file:
            return await file.read()
    except FileNotFoundError:
        return None
    except OSError:
        return None
