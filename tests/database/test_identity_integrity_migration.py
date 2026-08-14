from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa
from sqlalchemy import create_engine


def _identity_tables(metadata: sa.MetaData) -> tuple[sa.Table, ...]:
    users = sa.Table(
        "lingchu_identity_users",
        metadata,
        sa.Column("uid", sa.String(64), primary_key=True),
    )
    groups = sa.Table(
        "lingchu_platform_identity_groups",
        metadata,
        sa.Column("group_id", sa.String(128), primary_key=True),
        sa.Column("parent_group_id", sa.String(128)),
    )
    accounts = sa.Table(
        "lingchu_platform_accounts",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uid", sa.String(64), nullable=False),
    )
    memberships = sa.Table(
        "lingchu_identity_memberships",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uid", sa.String(64), nullable=False),
        sa.Column("group_id", sa.String(128), nullable=False),
        sa.Column("scope_type", sa.String(64), nullable=False),
        sa.Column("scope_id", sa.String(128)),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("source", sa.String(64)),
    )
    grants = sa.Table(
        "lingchu_permission_grants",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.String(128), nullable=False),
    )
    return users, groups, accounts, memberships, grants


def test_identity_integrity_migration_backfills_and_roundtrips() -> None:
    module_name = ".".join((
        "src.plugins.nonebot_plugin_lingchu_bot.migrations",
        "d7e8f9a0b1c2_identity_integrity",
    ))
    migration = import_module(module_name)
    engine = create_engine("sqlite://")
    try:
        metadata = sa.MetaData()
        users, groups, accounts, memberships, grants = _identity_tables(metadata)
        metadata.create_all(engine)

        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.execute(users.insert(), [{"uid": "u1"}])
            connection.execute(groups.insert(), [{"group_id": "g1"}])
            connection.execute(
                accounts.insert(),
                [{"id": 1, "uid": "u1"}],
            )
            connection.execute(
                memberships.insert(),
                [
                    {
                        "id": 1,
                        "uid": "u1",
                        "group_id": "g1",
                        "scope_type": "global",
                        "scope_id": None,
                        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
                        "source": "old",
                    },
                    {
                        "id": 2,
                        "uid": "u1",
                        "group_id": "g1",
                        "scope_type": "global",
                        "scope_id": None,
                        "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
                        "source": "new",
                    },
                    {
                        "id": 3,
                        "uid": "u1",
                        "group_id": "system.superusers",
                        "scope_type": "global",
                        "scope_id": None,
                        "updated_at": datetime(2026, 1, 3, tzinfo=UTC),
                        "source": "superusers_config",
                    },
                ],
            )
            connection.execute(
                groups.insert(),
                [{"group_id": "system.superusers"}],
            )
            connection.execute(grants.insert(), [{"id": 1, "group_id": "g1"}])
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, "op", operations):
                migration.upgrade()

            rows = connection.execute(
                sa.select(
                    memberships.c.id, memberships.c.scope_id, memberships.c.source
                )
            ).all()
            assert rows == [
                (2, "__lingchu_global_scope__", "new"),
                (3, "__lingchu_global_scope__", "superusers_config"),
            ]
            account_source = connection.execute(
                sa.text("SELECT source FROM lingchu_platform_accounts WHERE id = 1")
            ).scalar_one()
            assert account_source == "superusers_config"

            foreign_keys = connection.exec_driver_sql(
                "PRAGMA foreign_key_list('lingchu_identity_memberships')"
            ).all()
            assert {row[2] for row in foreign_keys} == {
                "lingchu_identity_users",
                "lingchu_platform_identity_groups",
            }

            with patch.object(migration, "op", operations):
                migration.downgrade()

            assert connection.execute(
                sa.select(memberships.c.scope_id)
            ).scalars().all() == [
                None,
                None,
            ]
    finally:
        engine.dispose()


def test_identity_integrity_migration_removes_orphan_rows() -> None:
    """Orphan rows referencing deleted users/groups are removed before FKs."""
    module_name = ".".join((
        "src.plugins.nonebot_plugin_lingchu_bot.migrations",
        "d7e8f9a0b1c2_identity_integrity",
    ))
    migration = import_module(module_name)
    engine = create_engine("sqlite://")
    try:
        metadata = sa.MetaData()
        users, groups, accounts, memberships, grants = _identity_tables(metadata)
        metadata.create_all(engine)

        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.execute(users.insert(), [{"uid": "u1"}])
            connection.execute(
                groups.insert(),
                [
                    {"group_id": "g1", "parent_group_id": None},
                    {"group_id": "orphan-child", "parent_group_id": "ghost-parent"},
                ],
            )
            connection.execute(
                accounts.insert(),
                [
                    {"id": 1, "uid": "u1"},
                    {"id": 2, "uid": "ghost-user"},  # orphan uid
                ],
            )
            connection.execute(
                memberships.insert(),
                [
                    {
                        "id": 1,
                        "uid": "u1",
                        "group_id": "g1",
                        "scope_type": "global",
                        "scope_id": None,
                        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
                        "source": "manual",
                    },
                    {
                        "id": 2,
                        "uid": "ghost-user",  # orphan uid
                        "group_id": "g1",
                        "scope_type": "global",
                        "scope_id": None,
                        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
                        "source": "manual",
                    },
                    {
                        "id": 3,
                        "uid": "u1",
                        "group_id": "ghost-group",  # orphan group_id
                        "scope_type": "global",
                        "scope_id": None,
                        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
                        "source": "manual",
                    },
                ],
            )
            connection.execute(
                grants.insert(),
                [
                    {"id": 1, "group_id": "g1"},
                    {"id": 2, "group_id": "ghost-group"},  # orphan group_id
                ],
            )

            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, "op", operations):
                migration.upgrade()

            assert connection.execute(
                sa.select(accounts.c.id).order_by(accounts.c.id)
            ).scalars().all() == [1]
            assert connection.execute(
                sa.select(memberships.c.id).order_by(memberships.c.id)
            ).scalars().all() == [1]
            assert connection.execute(
                sa.select(grants.c.id).order_by(grants.c.id)
            ).scalars().all() == [1]
            parent_ids = connection.execute(
                sa.select(groups.c.group_id, groups.c.parent_group_id)
            ).all()
            parent_map: dict[str, str | None] = {}
            for group_id, parent_group_id in parent_ids:
                parent_map[str(group_id)] = (
                    str(parent_group_id) if parent_group_id is not None else None
                )
            assert parent_map == {
                "g1": None,
                "orphan-child": None,  # dangling parent_group_id reset to NULL
            }

            # FK creation must succeed on the cleaned data.
            foreign_keys = connection.exec_driver_sql(
                "PRAGMA foreign_key_list('lingchu_identity_memberships')"
            ).all()
            assert {row[2] for row in foreign_keys} == {
                "lingchu_identity_users",
                "lingchu_platform_identity_groups",
            }
    finally:
        engine.dispose()
