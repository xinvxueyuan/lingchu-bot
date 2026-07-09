"""blocklist unique constraint

迁移 ID: cf2c06d51a17
父迁移: c3d4e5f6a7b8
创建时间: 2026-07-04 01:56:06

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "cf2c06d51a17"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "uq_lingchu_blocklist_entry_identity"
_TABLE = "lingchu_blocklist_entries"
_NEW_COLUMNS = ["platform_id", "adapter_id", "bot_id", "scope", "scope_key", "user_id"]
_OLD_COLUMNS = [
    "platform_id",
    "adapter_id",
    "protocol_id",
    "bot_id",
    "scope",
    "scope_key",
    "user_id",
]

# MySQL / MariaDB / SQL Server reflect table-level UniqueConstraint as a
# unique **index**. On these dialects, ``DROP INDEX`` is the correct way
# to remove it; ``ALTER TABLE DROP CONSTRAINT`` is unsupported or also
# removes the backing index in a way that ``batch_alter_table`` mishandles.
# Oracle reflects it as an index too, but ``DROP INDEX`` fails with
# ORA-02429 (index enforces unique key) — ``DROP CONSTRAINT`` works.
# PostgreSQL / SQLite reflect it as a named constraint.
_INDEX_DIALECTS = frozenset({"mysql", "mariadb", "mssql"})


def _replace_unique(columns: list[str]) -> None:
    """Drop and recreate the blocklist unique constraint cross-database.

    - SQLite: requires ``batch_alter_table`` for constraint changes.
    - MySQL / MariaDB / SQL Server: unique constraint stored as index;
      ``batch_alter_table(recreate="always")`` causes PK name conflicts on
      SQL Server, so use direct ``DROP INDEX`` + ``ADD CONSTRAINT``.
    - PostgreSQL / Oracle: direct ``ALTER TABLE DROP CONSTRAINT`` works.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table(_TABLE, recreate="always") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT_NAME, type_="unique")
            batch_op.create_unique_constraint(_CONSTRAINT_NAME, columns)
    elif dialect in _INDEX_DIALECTS:
        op.drop_index(_CONSTRAINT_NAME, table_name=_TABLE)
        op.create_unique_constraint(_CONSTRAINT_NAME, _TABLE, columns)
    else:
        op.drop_constraint(_CONSTRAINT_NAME, _TABLE, type_="unique")
        op.create_unique_constraint(_CONSTRAINT_NAME, _TABLE, columns)


def upgrade(name: str = "") -> None:
    if name:
        return

    _replace_unique(_NEW_COLUMNS)


def downgrade(name: str = "") -> None:
    if name:
        return

    _replace_unique(_OLD_COLUMNS)
