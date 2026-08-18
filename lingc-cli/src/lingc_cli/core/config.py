"""Global runtime configuration shared by all `lc` subcommands.

Mirrors nb-cli's `ConfigManager` globals pattern: options parsed at the root
CLI callback (`--cwd` / `--python` / `--venv`) are stored here so any
command or handler can read them without re-parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class _RuntimeConfig:
    cwd: Path | None = None
    python: str | None = None
    use_venv: bool = True


_runtime = _RuntimeConfig()


def set_cwd(value: str | None) -> None:
    """Set the working directory (resolved to an absolute `Path`)."""
    _runtime.cwd = Path(value).expanduser().resolve() if value else None


def get_cwd() -> Path | None:
    """Return the configured working directory, or `None`."""
    return _runtime.cwd


def set_python(value: str | None) -> None:
    """Set the Python executable path override."""
    _runtime.python = value


def get_python() -> str | None:
    """Return the Python executable path override, or `None`."""
    return _runtime.python


def set_use_venv(value: bool) -> None:
    """Set whether virtual-environment detection is enabled."""
    _runtime.use_venv = value


def get_use_venv() -> bool:
    """Return whether virtual-environment detection is enabled."""
    return _runtime.use_venv
