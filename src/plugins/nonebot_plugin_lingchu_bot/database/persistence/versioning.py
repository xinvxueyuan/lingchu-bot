"""Format versioning and migration for persisted TOML files.

A version line is written at the top of the file (next to the schema
reference) so future program versions can detect and migrate older files.
Files without a version line are treated as version 1 (the initial format).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

_VERSION_PREFIX = "# lingchu-version: "
_CURRENT_VERSION = 1

# Migration registry: version -> callable(old_content) -> new_content.
# Migrations run in ascending order until the current version is reached.
MIGRATIONS: dict[int, Callable[[str], str]] = {}


def current_version() -> int:
    """Return the format version this program writes."""
    return _CURRENT_VERSION


def read_version(content: str) -> int:
    """Read the format version from content; legacy files default to 1."""
    for line in content.splitlines():
        if line.startswith(_VERSION_PREFIX):
            try:
                return int(line[len(_VERSION_PREFIX) :].strip())
            except ValueError:
                return 1
        if line and not line.startswith("#"):
            break
    return 1


def write_version(content: str, version: int = _CURRENT_VERSION) -> str:
    """Prepend a version line to TOML content."""
    return f"{_VERSION_PREFIX}{version}\n{content}"


def migrate_content(content: str) -> str:
    """Migrate content to the current format version.

    Returns the migrated content. When no migration is needed the input is
    returned unchanged.
    """
    version = read_version(content)
    if version >= _CURRENT_VERSION:
        return content
    # Strip the old version line so migrations operate on the TOML body.
    lines = [
        line for line in content.splitlines() if not line.startswith(_VERSION_PREFIX)
    ]
    body = "\n".join(lines)
    for target in range(version, _CURRENT_VERSION):
        migration = MIGRATIONS.get(target)
        if migration is None:
            continue
        body = migration(body)
    return write_version(body, _CURRENT_VERSION)
