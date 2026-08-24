"""Environment snapshot for Lingc CLI (lc env).

Probes the current runtime and project with only stdlib metadata /
interpreter introspection — never imports NoneBot or plugin internals.
"""

from __future__ import annotations

import importlib.metadata
import shutil
import sys
from typing import TYPE_CHECKING

from lingc_cli.core.meta import resolve_python

if TYPE_CHECKING:
    from pathlib import Path

_ADAPTER_PREFIX = "nonebot-adapter-"
_LINGCHU_PACKAGE = "nonebot-plugin-lingchu-bot"


def list_adapters() -> list[tuple[str, str]]:
    """Return installed nonebot-adapter-* packages as (name, version) pairs."""
    result: list[tuple[str, str]] = []
    for dist in importlib.metadata.distributions():
        name = (dist.metadata.get("Name") or "").lower()
        if name.startswith(_ADAPTER_PREFIX):
            result.append((name, dist.version))
    return sorted(result)


def package_version(name: str) -> str | None:
    """Return the installed version of a distribution, or None if absent."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def venv_status(root: Path) -> str:
    """Describe the virtual-environment state relative to the project."""
    if sys.prefix != sys.base_prefix:
        return "active"
    if (root / ".venv").is_dir():
        return "found"
    return "missing"


def env_snapshot(root: Path) -> dict[str, object]:
    """Build a JSON-serializable snapshot of the environment."""
    return {
        "os": sys.platform,
        "python_version": sys.version.split()[0],
        "python_path": resolve_python(root),
        "uv": shutil.which("uv") is not None,
        "pip": shutil.which("pip") is not None,
        "adapters": [
            {"name": name, "version": version} for name, version in list_adapters()
        ],
        "lingchu_bot_version": package_version(_LINGCHU_PACKAGE),
        "venv": venv_status(root),
        "project_root": str(root),
    }


__all__ = ["env_snapshot", "list_adapters", "package_version", "venv_status"]
