"""Project scaffolding for Lingc CLI (lc init).

Generates the minimal `.env` template for a Lingchu Bot project without
overwriting existing user configuration unless explicitly forced.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

MINIMAL_ENV = """\
NICKNAME=lingchu
ENVIRONMENT=dev
DRIVER=~fastapi+~httpx+~websockets
SUPERUSERS=[]
COMMAND_START=["/"]
HOST=127.0.0.1
PORT=8080
"""


def init_project(root: Path, *, force: bool = False) -> list[Path]:
    """Write a minimal `.env` if missing. Returns the generated file paths.

    Never overwrites an existing `.env` unless `force` is True.
    """
    env_file = root / ".env"
    if env_file.exists() and not force:
        return []
    env_file.write_text(MINIMAL_ENV, encoding="utf-8")
    return [env_file]


__all__ = ["MINIMAL_ENV", "init_project"]
