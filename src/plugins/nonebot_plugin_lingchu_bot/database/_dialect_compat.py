"""跨数据库方言类型兼容层。

为受支持的四个后端（SQLite / PostgreSQL / MySQL / MariaDB）提供稳定的类型
映射。Oracle / SQL Server 方言支持已废弃，相关变体已移除。

Cross-database dialect type compatibility layer.

Keeps ORM models portable across the four supported backends (SQLite /
PostgreSQL / MySQL / MariaDB). Oracle / SQL Server support has been dropped.
Retained nuance:

- MySQL / MariaDB: DateTime(timezone=True) is compiled to DATETIME(6)
  (a warning is logged; writes use datetime.now(UTC) so no drift occurs).
- Boolean / Text / String use the standard SQLAlchemy types on all four
  backends and need no variant.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Boolean as SABoolean,
    DateTime as SADateTime,
    String as SAString,
    Text as SAText,
)
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME

# Boolean: native on SQLite/PG and MySQL 8.0.3+/MariaDB 10.2+ (TINYINT(1)).
CompatBoolean = SABoolean()

# Timestamps: MySQL/MariaDB lack timezone support and store DATETIME(6); the
# other dialects use the native timezone-aware type. Writes use UTC.
CompatDateTimeTZ = SADateTime(timezone=True).with_variant(
    MYSQL_DATETIME(fsp=6),
    "mysql",
    "mariadb",
)

# Text: native on all four backends.
CompatText = SAText()


def compat_string(length: int) -> Any:
    """Build a cross-dialect ``VARCHAR(length)`` (unified across all backends).

    Args:
        length: Maximum string length.

    Returns:
        A standard ``VARCHAR(length)`` SQLAlchemy type instance.
    """
    return SAString(length)


__all__ = (
    "CompatBoolean",
    "CompatDateTimeTZ",
    "CompatText",
    "compat_string",
)
