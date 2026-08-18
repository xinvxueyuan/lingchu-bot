"""Minimal gettext-style i18n shim for Lingc CLI messages."""

from __future__ import annotations

import gettext


def _gettext(message: str) -> str:
    """Translate a message via the process locale (no-op without catalogs)."""
    return gettext.gettext(message)


_ = _gettext
