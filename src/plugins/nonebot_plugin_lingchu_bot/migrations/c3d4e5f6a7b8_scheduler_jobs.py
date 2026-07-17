"""scheduler jobs

迁移 ID: c3d4e5f6a7b8
父迁移: b7c8d9e0f1a2
创建时间: 2026-07-02 00:00:00

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.dialects.oracle import NUMBER as ORACLE_NUMBER

if TYPE_CHECKING:
    from collections.abc import Sequence

CompatBoolean = sa.Boolean().with_variant(
    ORACLE_NUMBER(1, asdecimal=False),
    "oracle",
)
CompatDateTimeTZ = sa.DateTime(timezone=True).with_variant(
    MYSQL_DATETIME(fsp=6),
    "mysql",
    "mariadb",
)

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ``job_id`` 由 ``UniqueConstraint`` 在所有方言上都已建立唯一索引，
# 迁移不再额外创建 ``ix_lingchu_scheduled_jobs_job_id``，避免与
# 模型的 schema 声明冲突（同时绕开 Oracle ORA-01408）。
_SCHEDULED_JOBS_INDEX_COLUMNS: tuple[str, ...] = (
    "handler_key",
    "enabled",
    "created_at",
    "updated_at",
)


def upgrade(name: str = "") -> None:
    if name:
        return

    op.create_table(
        "lingchu_scheduled_jobs",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("handler_key", sa.String(length=128), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_kwargs", sa.Text(), nullable=False),
        sa.Column("args", sa.Text(), nullable=False),
        sa.Column("kwargs", sa.Text(), nullable=False),
        sa.Column("enabled", CompatBoolean, nullable=False),
        sa.Column("coalesce", CompatBoolean, nullable=False),
        sa.Column("max_instances", sa.Integer(), nullable=False),
        sa.Column("misfire_grace_time", sa.Integer(), nullable=True),
        sa.Column("created_at", CompatDateTimeTZ, nullable=False),
        sa.Column("updated_at", CompatDateTimeTZ, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_scheduled_jobs")),
        sa.UniqueConstraint(
            "job_id",
            name=op.f("uq_lingchu_scheduled_jobs_job_id"),
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    for column in _SCHEDULED_JOBS_INDEX_COLUMNS:
        op.create_index(
            op.f(f"ix_lingchu_scheduled_jobs_{column}"),
            "lingchu_scheduled_jobs",
            [column],
            unique=False,
        )


def downgrade(name: str = "") -> None:
    if name:
        return

    for column in tuple(reversed(_SCHEDULED_JOBS_INDEX_COLUMNS)):
        op.drop_index(
            op.f(f"ix_lingchu_scheduled_jobs_{column}"),
            table_name="lingchu_scheduled_jobs",
        )
    op.drop_table("lingchu_scheduled_jobs")
