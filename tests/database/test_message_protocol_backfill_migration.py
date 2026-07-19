from __future__ import annotations

from importlib import import_module
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa
from sqlalchemy import create_engine


def _message_table(metadata: sa.MetaData, name: str) -> sa.Table:
    return sa.Table(
        name,
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.String(64), nullable=False),
        sa.Column("adapter_id", sa.String(64), nullable=False),
        sa.Column("protocol_id", sa.String(64), nullable=True),
    )


def test_message_protocol_backfill_is_exact_and_downgrade_is_non_reversing() -> None:
    module_name = ".".join((
        "src.plugins.nonebot_plugin_lingchu_bot.migrations",
        "f6a7b8c9d0e1_message_protocol_default",
    ))
    migration = import_module(module_name)
    engine = create_engine("sqlite://")
    metadata = sa.MetaData()
    generic = _message_table(metadata, "lingchu_message_records")
    partition = _message_table(
        metadata,
        "lingchu_qq_onebot_v11_nonebot_event_records",
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        for table in (generic, partition):
            connection.execute(
                table.insert(),
                [
                    {
                        "id": 1,
                        "platform_id": "qq",
                        "adapter_id": "~onebot.v11",
                        "protocol_id": None,
                    },
                    {
                        "id": 2,
                        "platform_id": "qq",
                        "adapter_id": "~onebot.v11",
                        "protocol_id": "napcat",
                    },
                    {
                        "id": 3,
                        "platform_id": "matrix",
                        "adapter_id": "matrix.v1",
                        "protocol_id": None,
                    },
                ],
            )
        operations = Operations(MigrationContext.configure(connection))
        with patch.object(migration, "op", operations):
            migration.upgrade()
            migration.downgrade()

        for table in (generic, partition):
            rows = connection.execute(
                sa.select(table.c.id, table.c.protocol_id).order_by(table.c.id)
            ).all()
            assert rows == [(1, "default"), (2, "napcat"), (3, None)]
