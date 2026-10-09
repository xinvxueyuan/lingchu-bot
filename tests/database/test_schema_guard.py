"""schema_guard 自检模块的测试：纯函数比对、SQLite 实际索引读取、告警路径。"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
import sqlalchemy as sa

from src.plugins.nonebot_plugin_lingchu_bot.database import schema_guard
from src.plugins.nonebot_plugin_lingchu_bot.database.models import BlocklistEntry

if TYPE_CHECKING:
    from collections.abc import Iterator

BLOCKLIST_TABLE = "lingchu_blocklist_entries"
BLOCKLIST_IDENTITY = [
    "platform_id",
    "adapter_id",
    "bot_id",
    "scope",
    "scope_key",
    "user_id",
]

UNIQUE_INDEX_TABLE_DDL = f"""
CREATE TABLE {BLOCKLIST_TABLE} (
    id INTEGER NOT NULL PRIMARY KEY,
    platform_id VARCHAR(64) NOT NULL,
    adapter_id VARCHAR(64) NOT NULL,
    protocol_id VARCHAR(64) NOT NULL,
    bot_id VARCHAR(128) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    scope_key VARCHAR(128) NOT NULL,
    user_id VARCHAR(128) NOT NULL
)
"""

UNIQUE_INDEX_DDL = f"""
CREATE UNIQUE INDEX uq_blocklist_identity ON {BLOCKLIST_TABLE} (
    platform_id, adapter_id, bot_id, scope, scope_key, user_id
)
"""

STALE_TABLE_DDL = f"""
CREATE TABLE {BLOCKLIST_TABLE} (
    id INTEGER NOT NULL PRIMARY KEY,
    platform_id VARCHAR(64) NOT NULL,
    adapter_id VARCHAR(64) NOT NULL,
    protocol_id VARCHAR(64) NOT NULL,
    bot_id VARCHAR(128) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    scope_key VARCHAR(128) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    CONSTRAINT uq_stale UNIQUE (
        platform_id, adapter_id, protocol_id, bot_id, scope, scope_key, user_id
    )
)
"""


@pytest.fixture
def engine() -> Iterator[sa.Engine]:
    """提供内存 SQLite 引擎。"""
    local = sa.create_engine("sqlite://")
    try:
        yield local
    finally:
        local.dispose()


def test_report_flags_missing_declared_target() -> None:
    declared = {BLOCKLIST_TABLE: {frozenset(BLOCKLIST_IDENTITY)}}
    actual = {BLOCKLIST_TABLE: {frozenset({"id"})}}

    lines = schema_guard.schema_drift_report(declared, actual)

    assert len(lines) == 1
    assert BLOCKLIST_TABLE in lines[0]
    assert "adapter_id" in lines[0]


def test_report_ignores_extra_database_target() -> None:
    declared = {BLOCKLIST_TABLE: {frozenset(BLOCKLIST_IDENTITY)}}
    actual = {
        BLOCKLIST_TABLE: {
            frozenset(BLOCKLIST_IDENTITY),
            frozenset({"other_id"}),
        }
    }

    assert schema_guard.schema_drift_report(declared, actual) == []


def test_report_skips_table_absent_from_actual() -> None:
    declared = {BLOCKLIST_TABLE: {frozenset(BLOCKLIST_IDENTITY)}}

    assert schema_guard.schema_drift_report(declared, {}) == []


def test_collect_declared_targets_includes_blocklist_identity() -> None:
    declared = schema_guard.collect_declared_unique_targets()

    assert frozenset(BLOCKLIST_IDENTITY) in declared[BLOCKLIST_TABLE]
    assert all(isinstance(table, str) for table in declared)


def test_inspection_matches_model_when_table_created_from_metadata(
    engine: sa.Engine,
) -> None:
    """表由模型元数据建出时，自检必须判定无漂移（同时验证 PRAGMA 读表级 UNIQUE）。"""
    BlocklistEntry.__table__.create(engine)
    declared = {BLOCKLIST_TABLE: {frozenset(BLOCKLIST_IDENTITY)}}

    with engine.connect() as connection:
        actual = schema_guard.read_actual_unique_targets(connection, (BLOCKLIST_TABLE,))

    assert schema_guard.schema_drift_report(declared, actual) == []


def test_inspection_detects_stale_unique_constraint(engine: sa.Engine) -> None:
    """复刻生产库的旧形态：唯一约束多了 protocol_id，模型的 6 列目标就不存在了。"""
    with engine.begin() as connection:
        connection.exec_driver_sql(STALE_TABLE_DDL)
    declared = {BLOCKLIST_TABLE: {frozenset(BLOCKLIST_IDENTITY)}}

    with engine.connect() as connection:
        actual = schema_guard.read_actual_unique_targets(connection, (BLOCKLIST_TABLE,))

    lines = schema_guard.schema_drift_report(declared, actual)
    assert len(lines) == 1
    assert "在数据库中不存在" in lines[0]


def test_inspection_reads_plain_unique_index(engine: sa.Engine) -> None:
    """唯一性由 ``CREATE UNIQUE INDEX``（而非表级 UNIQUE 约束）提供时也必须读到。"""
    with engine.begin() as connection:
        connection.exec_driver_sql(UNIQUE_INDEX_TABLE_DDL)
        connection.exec_driver_sql(UNIQUE_INDEX_DDL)
    declared = {BLOCKLIST_TABLE: {frozenset(BLOCKLIST_IDENTITY)}}

    with engine.connect() as connection:
        actual = schema_guard.read_actual_unique_targets(connection, (BLOCKLIST_TABLE,))

    assert schema_guard.schema_drift_report(declared, actual) == []


def test_inspection_reports_unknown_table_as_empty(engine: sa.Engine) -> None:
    with engine.connect() as connection:
        actual = schema_guard.read_actual_unique_targets(connection, ("missing_table",))

    assert actual == {"missing_table": set()}


@pytest.mark.asyncio
async def test_log_schema_drift_warns_for_each_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = MagicMock()
    monkeypatch.setattr(
        schema_guard, "find_schema_drift", AsyncMock(return_value=["a", "b"])
    )
    monkeypatch.setattr(schema_guard.logger, "warning", warning)

    await schema_guard.log_schema_drift()

    assert warning.call_count == 3


@pytest.mark.asyncio
async def test_log_schema_drift_is_silent_without_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = MagicMock()
    monkeypatch.setattr(schema_guard, "find_schema_drift", AsyncMock(return_value=[]))
    monkeypatch.setattr(schema_guard.logger, "warning", warning)

    await schema_guard.log_schema_drift()

    warning.assert_not_called()


@pytest.mark.asyncio
async def test_log_schema_drift_never_breaks_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """自检自身异常必须被吞掉，不能影响启动。"""
    monkeypatch.setattr(
        schema_guard,
        "find_schema_drift",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    await schema_guard.log_schema_drift()


@pytest.mark.asyncio
async def test_find_schema_drift_returns_empty_when_no_declared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(schema_guard, "collect_declared_unique_targets", dict)

    assert await schema_guard.find_schema_drift() == []
