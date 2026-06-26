"""跨数据库方言类型兼容层。

为不同 SQL 方言提供 SQLAlchemy ``with_variant`` 类型，确保 6 个后端
（SQLite / PostgreSQL / MySQL / MariaDB / Oracle / SQL Server）上的
类型映射与 upsert 行为一致。

Cross-database dialect type compatibility layer.

Provides SQLAlchemy ``with_variant`` types that keep ORM models portable
across all six supported backends (SQLite / PostgreSQL / MySQL / MariaDB /
Oracle / SQL Server). Goals:

- MySQL / MariaDB: ``DateTime(timezone=True)`` is compiled to ``DATETIME(6)``
  (a warning is logged; writes use ``datetime.now(UTC)`` so no drift occurs).
- Oracle pre-23c: ``BOOLEAN`` is mapped to ``NUMBER(1)``; ``TEXT`` is mapped
  to ``CLOB`` to avoid ``VARCHAR2(4000)`` truncation. Identifier length is
  limited to 128 characters (Oracle 12.2+ requirement).
- SQL Server: ``BOOLEAN`` is mapped to ``BIT``; ``String(N)`` for ``N > 4000``
  is mapped to ``NVARCHAR(MAX)`` (not currently needed: all ``String``
  lengths in this repo are ≤ 128).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Boolean as SABoolean,
)
from sqlalchemy import (
    DateTime as SADateTime,
)
from sqlalchemy import (
    String as SAString,
)
from sqlalchemy import (
    Text as SAText,
)
from sqlalchemy.dialects.mssql import NVARCHAR as MSSQL_NVARCHAR
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.dialects.oracle import CLOB as ORACLE_CLOB
from sqlalchemy.dialects.oracle import NUMBER as ORACLE_NUMBER

# SQL Server ``NVARCHAR`` 上限 4000；超过时切到 ``NVARCHAR(MAX)``。
# SQL Server ``NVARCHAR`` upper bound; switch to ``NVARCHAR(MAX)`` above it.
_MSSQL_NVARCHAR_MAX = 4000

# 布尔：Oracle pre-23c 缺 BOOLEAN，映射 NUMBER(1)。
# Boolean: Oracle pre-23c lacks BOOLEAN; map to NUMBER(1).
CompatBoolean = SABoolean().with_variant(
    ORACLE_NUMBER(1, asdecimal=False),
    "oracle",
)

# 时间戳：MySQL / MariaDB 缺时区支持，存为 DATETIME(6)；其余方言用原生支持。
# 写入侧使用 datetime.now(UTC) 可避免时区漂移。
# Timestamps: MySQL / MariaDB lack timezone support and store DATETIME(6);
# all other dialects use the native timezone-aware type. Writes use
# datetime.now(UTC) so no drift occurs in practice.
CompatDateTimeTZ = SADateTime(timezone=True).with_variant(
    MYSQL_DATETIME(fsp=6),
    "mysql",
    "mariadb",
)

# 文本：Oracle 映射 CLOB，避免 VARCHAR2(4000) 截断长文本。
# Text: Oracle maps to CLOB to avoid VARCHAR2(4000) truncation.
CompatText = SAText().with_variant(ORACLE_CLOB, "oracle")


def compat_string(length: int) -> Any:
    """构造跨方言兼容的 ``String(length)``。

    Args:
        length: 字符串长度上限 / Maximum string length.

    Returns:
        SQLAlchemy 类型实例；当 ``length > 4000`` 时在 SQL Server 上变体为
        ``NVARCHAR(MAX)``，在 Oracle 上变体为 ``CLOB``。其它方言使用默认
        ``VARCHAR(length)`` 即可。

        A SQLAlchemy type instance. When ``length > 4000`` the SQL Server
        variant is ``NVARCHAR(MAX)``; the Oracle variant is ``CLOB``. All
        other dialects use the default ``VARCHAR(length)``.
    """
    base = SAString(length)
    if length > _MSSQL_NVARCHAR_MAX:
        return base.with_variant(MSSQL_NVARCHAR(None), "mssql")
    return base.with_variant(ORACLE_CLOB, "oracle")


__all__ = (
    "CompatBoolean",
    "CompatDateTimeTZ",
    "CompatText",
    "compat_string",
)
