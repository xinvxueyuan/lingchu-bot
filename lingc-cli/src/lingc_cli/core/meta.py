"""Project root and Python interpreter resolution for Lingc CLI.

Shared stable contract used by the run / env / doctor / lifecycle handlers so
they can agree on "where is the project" and "which Python to spawn".
"""

from __future__ import annotations

from pathlib import Path

from lingc_cli.core import config

_PROJECT_MARKERS = ("pyproject.toml", "bot.py")
_VENV_PYTHONS = ("Scripts/python.exe", "bin/python")


def project_root(cwd: Path | None = None) -> Path:
    """Resolve the project root, walking upward for a project marker."""
    start = (cwd or config.get_cwd() or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if any((candidate / marker).exists() for marker in _PROJECT_MARKERS):
            return candidate
    return start


def resolve_python(cwd: Path | None = None) -> str:
    """Resolve the Python executable honoring the python override and venv detection."""
    override = config.get_python()
    if override:
        return override
    if config.get_use_venv():
        root = project_root(cwd)
        for rel in _VENV_PYTHONS:
            candidate = root / ".venv" / rel
            if candidate.is_file():
                return str(candidate)
    return "python"
