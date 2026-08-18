"""Shared constants for Lingc CLI."""

from __future__ import annotations

import sys

PROG = "lc"
WINDOWS = sys.platform.startswith("win")
REQUIRES_PYTHON = (3, 13)
DEFAULT_STARTUP_TIMEOUT = 30
STARTUP_MARKER = "Application startup complete."
