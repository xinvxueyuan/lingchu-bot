"""Unified persistence layer: integrity, atomicity, recovery, journaling.

This package provides the building blocks for reliable disk persistence of
Lingchu's TOML-backed state:

- :mod:`.checksum` — content integrity verification (SHA-256 trailer line)
- :mod:`.atomic` — crash-safe atomic writes with pre-write backups
- :mod:`.journal` — append-only operation journal for auditability
- :mod:`.recovery` — corrupted-file recovery from backups
- :mod:`.versioning` — format versioning and migration hooks
"""

from __future__ import annotations

from .atomic import (
    atomic_write_text,
    backup_path,
    cleanup_stale_temp_files,
    read_text,
)
from .checksum import (
    append_checksum,
    compute_checksum,
    extract_checksum,
    verify_checksum,
)
from .journal import PersistenceJournal, journal_path
from .recovery import quarantine_corrupt, recover_file, verify_file
from .versioning import (
    MIGRATIONS,
    current_version,
    migrate_content,
    read_version,
    write_version,
)

__all__ = [
    "MIGRATIONS",
    "PersistenceJournal",
    "append_checksum",
    "atomic_write_text",
    "backup_path",
    "cleanup_stale_temp_files",
    "compute_checksum",
    "current_version",
    "extract_checksum",
    "journal_path",
    "migrate_content",
    "quarantine_corrupt",
    "read_text",
    "read_version",
    "recover_file",
    "verify_checksum",
    "verify_file",
    "write_version",
]
