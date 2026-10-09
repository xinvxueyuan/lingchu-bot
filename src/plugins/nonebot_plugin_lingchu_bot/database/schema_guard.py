"""数据库模式自检：比对模型声明的唯一目标与数据库实际的唯一索引。

为什么不依赖迁移就够了：生产库的表可能是早期 ``create_all`` 建的（或由外部工具改过），
而 ``create_all`` **不会**修改既有表结构；``ALEMBIC_STARTUP_CHECK=false`` 时 ORM 走
``migrate.sync``（alembic autogenerate 同步），在 SQLite 上识别唯一约束差异并不可靠。

一旦唯一索引与模型声明不一致，SQLite 的 ``ON CONFLICT`` 会在运行期报
``ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint``，在业务层
表现为「xxx失败，数据库异常: DatabaseError('Upsert failed')」。本模块在启动时**只读**
检查并输出告警，让这种漂移在日志里第一时间可见，且绝不阻断启动。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nonebot import logger, require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model, get_session
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from . import models as models_module
from .orm_crud._base import declared_unique_targets

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.ext.asyncio import AsyncConnection

#: 唯一目标集合的类型别名（表名 → 该表所有唯一目标的列名集合）。
UniqueTargets = dict[str, set[frozenset[str]]]


def collect_declared_unique_targets() -> UniqueTargets:
    """收集本插件全部模型声明的**非主键**唯一目标。

    Returns:
        表名到唯一目标集合的映射；没有声明唯一目标的模型不会出现在结果里。
    """
    declared: UniqueTargets = {}
    for name in getattr(models_module, "__all__", ()):
        model = getattr(models_module, name, None)
        if not isinstance(model, type) or not issubclass(model, Model):
            continue
        table_name = getattr(model, "__tablename__", None)
        if not isinstance(table_name, str):
            continue
        targets = declared_unique_targets(model)
        if targets:
            declared.setdefault(table_name, set()).update(targets)
    return declared


def _inspector_unique_targets(inspector: Any, table: str) -> set[frozenset[str]] | None:
    """用 inspector 读取唯一约束 / 唯一索引；读取失败时返回 None。"""
    found: set[frozenset[str]] = set()
    try:
        for constraint in inspector.get_unique_constraints(table):
            columns = constraint.get("column_names") or []
            if columns:
                found.add(frozenset(columns))
        for index in inspector.get_indexes(table):
            if index.get("unique"):
                columns = index.get("column_names") or []
                if columns:
                    found.add(frozenset(columns))
    except (SQLAlchemyError, NotImplementedError):
        logger.debug("Inspector cannot read unique targets for table {}", table)
        return None
    return found


def read_actual_unique_targets(
    connection: AsyncConnection | Any, tables: Iterable[str]
) -> UniqueTargets:
    """读取数据库里各表的实际唯一目标（同步函数，供 ``run_sync`` 调用）。

    Args:
        connection: 同步连接（``AsyncConnection.run_sync`` 会传入）。
        tables: 待检查的表名。

    Returns:
        表名到实际唯一目标集合的映射；表不存在或无法读取时为**空集合**（表示未知）。
    """
    inspector = inspect(connection)
    if inspector is None:  # pragma: no cover - 防御性分支，非 Connection 才可能为 None
        logger.debug("Inspector unavailable; skipping schema drift inspection")
        return {table: set() for table in tables}
    existing = set(inspector.get_table_names())
    actual: UniqueTargets = {}
    for table in tables:
        if table not in existing:
            actual[table] = set()
            continue
        found = _inspector_unique_targets(inspector, table)
        if found is None:
            actual[table] = set()
            continue
        actual[table] = found
    return actual


def schema_drift_report(declared: UniqueTargets, actual: UniqueTargets) -> list[str]:
    """比对声明与实际，返回不一致的说明列表（纯函数，便于测试）。

    只在「模型声明了某唯一目标、但数据库里读不到」时报告；数据库里多出来的唯一索引
    不影响 upsert，故不计入。
    """
    lines: list[str] = []
    for table in sorted(declared):
        present = actual.get(table)
        if present is None:
            continue
        lines.extend(
            f"{table}: 模型声明的唯一目标 ({','.join(sorted(target))}) 在数据库中不存在"
            for target in sorted(declared[table] - present, key=sorted)
        )
    return lines


async def find_schema_drift() -> list[str]:
    """只读检查数据库模式与模型声明的差异。

    Returns:
        差异说明列表；无差异或无法检查时为空列表（本函数不抛异常）。
    """
    declared = collect_declared_unique_targets()
    if not declared:
        return []
    try:
        async with get_session() as session:
            connection = await session.connection()
            actual = await connection.run_sync(
                read_actual_unique_targets, tuple(declared)
            )
    except (SQLAlchemyError, AttributeError, TypeError) as exc:
        logger.debug("Schema drift check skipped: {}", exc)
        return []
    return schema_drift_report(declared, actual)


async def log_schema_drift() -> None:
    """启动时只读自检：发现漂移只告警，绝不阻断启动。"""
    try:
        drift = await find_schema_drift()
    except Exception as exc:  # noqa: BLE001 - 自检不得影响启动流程
        logger.debug("Schema drift check failed: {}", exc)
        return
    if not drift:
        return
    logger.warning("数据库模式与模型声明不一致（{} 处）:", len(drift))
    for line in drift:
        logger.warning("  - {}", line)
