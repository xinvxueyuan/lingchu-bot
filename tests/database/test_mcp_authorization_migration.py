from __future__ import annotations

from importlib import import_module
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def test_mcp_authorization_migration_upgrades_and_downgrades_sqlite() -> None:
    migration = import_module(
        "src.plugins.nonebot_plugin_lingchu_bot.migrations."
        "e5f6a7b8c9d0_mcp_authorization"
    )
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        with patch.object(migration, "op", operations):
            migration.upgrade()
            tables = set(inspect(connection).get_table_names())
            assert "lingchu_mcp_service_principals" in tables
            assert "lingchu_mcp_resource_grants" in tables
            unique_columns = {
                tuple(constraint["column_names"])
                for constraint in inspect(connection).get_unique_constraints(
                    "lingchu_mcp_service_principals"
                )
            }
            assert ("issuer", "identity_kind", "identity_value") in unique_columns
            migration.downgrade()
            tables = set(inspect(connection).get_table_names())
            assert "lingchu_mcp_service_principals" not in tables
            assert "lingchu_mcp_resource_grants" not in tables
