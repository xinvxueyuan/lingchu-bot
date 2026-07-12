"""event partitions and subject policies

迁移 ID: b7c8d9e0f1a2
父迁移: a1b2c3d4e5f6
创建时间: 2026-06-24 01:30:00

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _event_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("platform_id", sa.String(length=64), nullable=False),
        sa.Column("adapter_id", sa.String(length=64), nullable=False),
        sa.Column("protocol_id", sa.String(length=64), nullable=True),
        sa.Column("framework_id", sa.String(length=64), nullable=False),
        sa.Column("bot_id", sa.String(length=128), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("message_id", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_category", sa.String(length=64), nullable=True),
        sa.Column("message_type", sa.String(length=64), nullable=True),
        sa.Column("text_summary", sa.Text(), nullable=True),
        sa.Column("raw_message", sa.Text(), nullable=True),
        sa.Column("raw_event", sa.Text(), nullable=True),
        sa.Column("process_status", sa.String(length=32), nullable=False),
        sa.Column("exception_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("platform_id", sa.String(length=64), nullable=False),
        sa.Column("adapter_id", sa.String(length=64), nullable=False),
        sa.Column("protocol_id", sa.String(length=64), nullable=True),
        sa.Column("framework_id", sa.String(length=64), nullable=False),
        sa.Column("bot_id", sa.String(length=128), nullable=False),
        sa.Column("audit_type", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("data_summary", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("exception_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _index_columns(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def upgrade(name: str = "") -> None:
    if name:
        return

    op.add_column(
        "lingchu_message_records",
        sa.Column(
            "framework_id",
            sa.String(length=64),
            nullable=False,
            server_default="nonebot",
        ),
    )
    op.add_column(
        "lingchu_message_records",
        sa.Column("event_category", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "lingchu_audit_records",
        sa.Column(
            "framework_id",
            sa.String(length=64),
            nullable=False,
            server_default="nonebot",
        ),
    )
    _index_columns(
        "lingchu_message_records",
        ("framework_id", "event_category"),
    )
    _index_columns("lingchu_audit_records", ("framework_id",))

    op.create_table(
        "lingchu_qq_onebot_v11_nonebot_event_records",
        *_event_columns(),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_lingchu_qq_onebot_v11_nonebot_event_records"),
        ),
        sa.UniqueConstraint(
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "conversation_id",
            "message_id",
            name="uq_lingchu_qq_ob11_nb_event_identity",
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    _index_columns(
        "lingchu_qq_onebot_v11_nonebot_event_records",
        (
            "platform_id",
            "adapter_id",
            "protocol_id",
            "framework_id",
            "bot_id",
            "conversation_id",
            "user_id",
            "message_id",
            "event_type",
            "event_category",
            "message_type",
            "process_status",
            "created_at",
            "updated_at",
        ),
    )

    op.create_table(
        "lingchu_qq_onebot_v11_nonebot_audit_records",
        *_audit_columns(),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_lingchu_qq_onebot_v11_nonebot_audit_records"),
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    _index_columns(
        "lingchu_qq_onebot_v11_nonebot_audit_records",
        (
            "platform_id",
            "adapter_id",
            "protocol_id",
            "framework_id",
            "bot_id",
            "audit_type",
            "event_type",
            "created_at",
        ),
    )

    op.create_table(
        "lingchu_subject_policy_entries",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("policy_type", sa.String(length=32), nullable=False),
        sa.Column("platform_id", sa.String(length=64), nullable=False),
        sa.Column("adapter_id", sa.String(length=64), nullable=False),
        sa.Column("protocol_id", sa.String(length=64), nullable=True),
        sa.Column("bot_id", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.String(length=128), nullable=False),
        sa.Column("group_id", sa.String(length=128), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("operator_id", sa.String(length=128), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_subject_policy_entries")),
        sa.UniqueConstraint(
            "policy_type",
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "scope",
            "scope_key",
            "user_id",
            name="uq_lingchu_subject_policy_identity",
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    _index_columns(
        "lingchu_subject_policy_entries",
        (
            "policy_type",
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "scope",
            "scope_key",
            "group_id",
            "user_id",
            "operator_id",
            "expires_at",
            "created_at",
            "updated_at",
        ),
    )


def downgrade(name: str = "") -> None:
    if name:
        return

    for table, columns in (
        (
            "lingchu_subject_policy_entries",
            (
                "updated_at",
                "created_at",
                "expires_at",
                "operator_id",
                "user_id",
                "group_id",
                "scope_key",
                "scope",
                "bot_id",
                "protocol_id",
                "adapter_id",
                "platform_id",
                "policy_type",
            ),
        ),
        (
            "lingchu_qq_onebot_v11_nonebot_audit_records",
            (
                "created_at",
                "event_type",
                "audit_type",
                "bot_id",
                "framework_id",
                "protocol_id",
                "adapter_id",
                "platform_id",
            ),
        ),
        (
            "lingchu_qq_onebot_v11_nonebot_event_records",
            (
                "updated_at",
                "created_at",
                "process_status",
                "message_type",
                "event_category",
                "event_type",
                "message_id",
                "user_id",
                "conversation_id",
                "bot_id",
                "framework_id",
                "protocol_id",
                "adapter_id",
                "platform_id",
            ),
        ),
    ):
        for column in columns:
            op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_table(table)

    op.drop_index(
        op.f("ix_lingchu_audit_records_framework_id"),
        table_name="lingchu_audit_records",
    )
    op.drop_index(
        op.f("ix_lingchu_message_records_event_category"),
        table_name="lingchu_message_records",
    )
    op.drop_index(
        op.f("ix_lingchu_message_records_framework_id"),
        table_name="lingchu_message_records",
    )
    op.drop_column("lingchu_audit_records", "framework_id")
    op.drop_column("lingchu_message_records", "event_category")
    op.drop_column("lingchu_message_records", "framework_id")
