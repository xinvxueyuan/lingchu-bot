"""Tests for pytest session configuration helpers."""

from __future__ import annotations

from tests.conftest import _should_check_alembic_on_startup


def test_alembic_startup_check_disabled_for_local_database() -> None:
    assert _should_check_alembic_on_startup(None, "master") is False


def test_alembic_startup_check_disabled_for_serial_external_database() -> None:
    assert _should_check_alembic_on_startup("sqlite+aiosqlite:///test.db", "master") is False


def test_alembic_startup_check_enabled_for_xdist_external_database() -> None:
    assert _should_check_alembic_on_startup("postgresql+psycopg://test", "gw0") is True
