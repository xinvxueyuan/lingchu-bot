"""SQLite PRAGMA tuning for better runtime concurrency and write performance."""

from __future__ import annotations

from typing import Any

from nonebot import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine


def _is_sqlite_connection(dbapi_connection: Any) -> bool:
    module_name = type(dbapi_connection).__module__
    return module_name.startswith("sqlite3") or "aiosqlite" in module_name


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    if not _is_sqlite_connection(dbapi_connection):
        return
    # aiosqlite connections arrive as SQLAlchemy's AsyncAdapt_aiosqlite_connection,
    # whose cursor()/execute()/close() are synchronous greenlet facades, so the
    # sync call sequence below is correct on both sqlite3 and aiosqlite paths.
    cursor = None
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
    except Exception as exc:
        logger.warning("Failed to apply SQLite PRAGMA optimizations: {}", exc)
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as exc:
                logger.warning("Failed to close SQLite PRAGMA cursor: {}", exc)
