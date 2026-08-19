from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database import sqlite_pragmas


class _FakeCursor:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.statements: list[str] = []
        self.closed = False
        self._fail_on = fail_on

    def execute(self, sql: str) -> None:
        if self._fail_on is not None and self._fail_on == sql:
            raise RuntimeError("boom")
        self.statements.append(sql)

    def close(self) -> None:
        self.closed = True


class _FakeSQLiteConnection:
    __module__ = "sqlite3"

    def __init__(self, *, fail_on: str | None = None) -> None:
        self.cursor_instance = _FakeCursor(fail_on=fail_on)

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance


class _FakePostgresConnection:
    __module__ = "psycopg"

    def __init__(self) -> None:
        self.cursor_called = False

    def cursor(self) -> _FakeCursor:
        self.cursor_called = True
        return _FakeCursor()


def test_set_sqlite_pragmas_applies_expected_statements() -> None:
    conn = _FakeSQLiteConnection()

    sqlite_pragmas._set_sqlite_pragmas(conn, None)

    assert conn.cursor_instance.statements == [
        "PRAGMA journal_mode=WAL;",
        "PRAGMA synchronous=NORMAL;",
        "PRAGMA busy_timeout=5000;",
    ]
    assert conn.cursor_instance.closed is True


def test_set_sqlite_pragmas_skips_non_sqlite_connections() -> None:
    conn = _FakePostgresConnection()

    sqlite_pragmas._set_sqlite_pragmas(conn, None)

    assert conn.cursor_called is False


def test_set_sqlite_pragmas_logs_warning_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _FakeSQLiteConnection(fail_on="PRAGMA synchronous=NORMAL;")
    warning = MagicMock()
    monkeypatch.setattr(sqlite_pragmas.logger, "warning", warning)

    sqlite_pragmas._set_sqlite_pragmas(conn, None)

    warning.assert_called_once()
    assert conn.cursor_instance.closed is True


async def test_pragmas_applied_through_real_async_engine(
    tmp_path: Path,
) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'pragma_check.db'}")
    try:
        async with engine.connect() as conn:
            mode = await conn.exec_driver_sql("PRAGMA journal_mode;")
            assert mode.scalar_one() == "wal"
            sync = await conn.exec_driver_sql("PRAGMA synchronous;")
            assert sync.scalar_one() == 1
    finally:
        await engine.dispose()
