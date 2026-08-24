"""Shared pytest fixtures for lingc-cli tests."""

from __future__ import annotations

import os

import pytest

# Pin the locale before any lingc_cli module is imported so import-time `_()`
# calls (e.g. Typer option help) resolve to English deterministically.
os.environ["LINGC_LOCALE"] = "en"


@pytest.fixture(autouse=True)
def _force_english_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep runtime messages English so output assertions are stable."""
    monkeypatch.setenv("LINGC_LOCALE", "en")
