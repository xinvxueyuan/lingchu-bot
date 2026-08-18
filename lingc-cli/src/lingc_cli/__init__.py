"""Lingc CLI — a convenience command-line tool for operating Lingchu Bot.

Provides safe startup, environment detection, package management,
diagnostics/repair and updates.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

_PACKAGE = "lingc-cli"

try:
    __version__ = version(_PACKAGE)
except PackageNotFoundError:  # running uninstalled (source checkout)
    __version__ = "0.1.0"
