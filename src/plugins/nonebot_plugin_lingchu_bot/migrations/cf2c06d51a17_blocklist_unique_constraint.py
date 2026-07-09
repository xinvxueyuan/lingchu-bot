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

    from alembic.operations.base import BatchOperations

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
# unique **index**; PostgreSQL / SQLite / Oracle reflect it as a named
# **constraint**. batch_alter_table's drop_constraint looks up the name in
# the reflected Table.constraints, so it raises KeyError on dialects where
# the unique constraint lives in Table.indexes instead.
_INDEX_DIALECTS = frozenset({"mysql", "mariadb", "mssql"})


def _drop_unique_in_batch(batch_op: BatchOperations, name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name in _INDEX_DIALECTS:
        batch_op.drop_index(name)
    else:
        batch_op.drop_constraint(name, type_="unique")


def upgrade(name: str = "") -> None:
    if name:
        return

    with op.batch_alter_table(_TABLE, recreate="always") as batch_op:
        _drop_unique_in_batch(batch_op, _CONSTRAINT_NAME)
        batch_op.create_unique_constraint(_CONSTRAINT_NAME, _NEW_COLUMNS)


def downgrade(name: str = "") -> None:
    if name:
        return

    with op.batch_alter_table(_TABLE, recreate="always") as batch_op:
        _drop_unique_in_batch(batch_op, _CONSTRAINT_NAME)
        batch_op.create_unique_constraint(_CONSTRAINT_NAME, _OLD_COLUMNS)
