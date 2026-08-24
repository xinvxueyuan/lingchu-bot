"""Append-only persistence operation journal.

Every write, delete, and recovery action is recorded as a single line in a
plain-text log so operators can audit what happened to persisted files and
diagnose corruption or unexpected changes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import aiofiles
import aiofiles.os

if TYPE_CHECKING:
    from pathlib import Path

_JOURNAL_FILENAME = "persistence.log"


def journal_path(directory: Path) -> Path:
    """Return the journal file path inside a persistence directory."""
    return directory / _JOURNAL_FILENAME


def _format_line(operation: str, path: Path, checksum: str | None, detail: str) -> str:
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds")
    checksum_part = checksum or "-"
    return f"{timestamp} | {operation} | {path} | {checksum_part} | {detail}\n"


class PersistenceJournal:
    """Append-only journal for persistence operations."""

    def __init__(self, directory: Path) -> None:
        self._path = journal_path(directory)

    async def record(
        self,
        operation: str,
        path: Path,
        *,
        checksum: str | None = None,
        detail: str = "",
    ) -> None:
        """Append one journal entry without blocking the event loop."""
        line = _format_line(operation, path, checksum, detail)
        try:
            await aiofiles.os.makedirs(self._path.parent, exist_ok=True)
            async with aiofiles.open(self._path, "a", encoding="utf-8") as file:
                await file.write(line)
        except OSError:
            # Journaling must never break the persistence operation itself.
            return

    async def read_entries(self) -> list[str]:
        """Return all journal lines (for tests and diagnostics)."""
        if not await aiofiles.os.path.exists(self._path):
            return []
        async with aiofiles.open(self._path, encoding="utf-8") as file:
            content = await file.read()
        return [line for line in content.splitlines() if line.strip()]
