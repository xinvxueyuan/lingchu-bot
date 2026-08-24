"""Recovery helpers for corrupted or interrupted persisted files.

On read, a file whose checksum does not match is treated as corrupted. The
recovery path tries the crash-safe backup (``<name>.bak``) written before the
last update; when the backup is intact it is restored in place. Otherwise the
caller falls back to defaults and the corrupted file is quarantined.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import aiofiles.os

from .atomic import atomic_write_text, backup_path, read_text
from .checksum import verify_checksum

if TYPE_CHECKING:
    from pathlib import Path

    from .journal import PersistenceJournal


async def verify_file(path: Path) -> bool:
    """Return True when the file is absent, unverifiable, or intact."""
    content = await read_text(path)
    if content is None:
        return True
    return verify_checksum(content)


async def recover_file(
    path: Path,
    journal: PersistenceJournal,
) -> str | None:
    """Restore a corrupted file from its backup.

    Returns the restored content, or None when no usable backup exists. The
    corrupted file is preserved as ``<name>.corrupt`` for forensics.
    """
    backup = backup_path(path)
    backup_content = await read_text(backup)
    if backup_content is None or not verify_checksum(backup_content):
        await journal.record(
            "recover_failed", path, detail="no intact backup available"
        )
        return None

    await _quarantine_corrupt(path)
    await atomic_write_text(path, backup_content)
    await journal.record("recovered", path, detail=f"restored from {backup.name}")
    return backup_content


async def _quarantine_corrupt(path: Path) -> None:
    """Move a corrupted file aside as ``<name>.corrupt``."""
    corrupt = path.with_name(f"{path.name}.corrupt")
    with contextlib.suppress(OSError):
        await aiofiles.os.replace(path, corrupt)


async def quarantine_corrupt(path: Path) -> None:
    """Public wrapper to quarantine a corrupted file (used when no backup)."""
    await _quarantine_corrupt(path)
