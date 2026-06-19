"""数据库 CRUD 工具。

提供基于 SQLAlchemy 异步引擎和 nonebot_plugin_orm 的通用增删查改操作。
所有函数均为异步实现；成功时直接返回结果，数据库异常时抛出 DatabaseError。
查询类函数使用 None 或空列表表示未找到记录，不把“未找到”与“数据库异常”混淆。

Database CRUD helpers.

This module provides generic asynchronous create, read, update, and delete
operations on ORM models backed by SQLAlchemy async sessions and
nonebot_plugin_orm. Successful calls return results directly, while database
failures raise DatabaseError.
Query helpers use None or empty lists to mean “not found”, keeping that case
separate from real database errors.
"""

# ruff: noqa: TRY003
from __future__ import annotations

from nonebot import require

require("nonebot_plugin_orm")
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any

from nonebot_plugin_orm import Model, get_session
from sqlalchemy import (
    Select,
    func,
    select,
)
from sqlalchemy import (
    delete as sqlalchemy_delete,
)
from sqlalchemy import (
    update as sqlalchemy_update,
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.inspection import inspect

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

logger = logging.getLogger(__name__)
ROWCOUNT_UNKNOWN = -1
_last_warn_time: dict[str, float] = {}
_WARN_INTERVAL = 60


class DatabaseError(Exception):
    """数据库操作失败时使用的统一异常。

    该异常只表示持久化层操作失败，不区分具体数据库驱动，也不
    封装业务语义。调用方应将其视为“数据库请求失败”，而不是
    “记录不存在”或“参数校验失败”。

    This is the shared exception for persistence-layer failures.
    It does not encode driver-specific details or business semantics.
    Callers should treat it as a database request failure, not as a
    “record not found” or “validation error” signal.
    """


def _is_fk_constraint_violation(e: IntegrityError) -> bool:
    """判断完整性错误是否为外键约束冲突。

    Args:
        e: SQLAlchemy 完整性错误对象 / SQLAlchemy integrity error.

    Returns:
        若判断为外键冲突则返回 True，否则返回 False。

    Raises:
        无 / None.
    """
    orig = e.orig
    sqlstate = getattr(orig, "sqlstate", None)
    if sqlstate is not None:
        try:
            return str(sqlstate) == "23503"
        except (AttributeError, TypeError):
            pass
    msg = str(orig).lower()
    return "foreign key" in msg


def _conds[T: Model](
    model: type[T],
    filters: dict[str, Any] | None,
) -> list[ColumnElement[bool]]:
    """构造筛选条件表达式列表。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 字段到筛选值的映射，None 表示不加条件 / Field-value map.

    Returns:
        SQLAlchemy 布尔表达式列表 / List of SQLAlchemy boolean expressions.

    Raises:
        ValueError: 筛选字段不存在时 / When a filter column is unknown.
    """
    if not filters:
        return []
    columns = _get_column_map(model)
    c: list[ColumnElement[bool]] = []
    for k, v in filters.items():
        col = columns.get(k)
        if col is None:
            raise ValueError(f"Unknown column '{k}' for model '{model.__name__}'")
        if v is None:
            c.append(col.is_(None))
        elif isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
            if len(v) == 0:
                logger.warning(
                    "Filter '%s' uses an empty sequence; will generate `col.in_([])`, "
                    "which never matches any records",
                    k,
                )
            c.append(col.in_(list(v)))
        else:
            c.append(col == v)
    return c


def _orders[T: Model](
    model: type[T],
    order_by: Sequence[str] | None,
) -> list[UnaryExpression[Any]]:
    """构造排序表达式列表。

    Args:
        model: ORM 模型类 / ORM model class.
        order_by: 排序字段列表，前缀为 - 表示降序 / Sort fields.

    Returns:
        排序表达式列表 / List of SQLAlchemy ordering expressions.

    Raises:
        无 / None.
    """
    if not order_by:
        return []
    o: list[UnaryExpression[Any]] = []
    for key in order_by:
        if key.startswith("-"):
            col = getattr(model, key[1:], None)
            if col is not None:
                o.append(col.desc())
            else:
                logger.warning(
                    "Sort field '%s' not found on model '%s', ignored",
                    key[1:],
                    model.__name__,
                )
        else:
            col = getattr(model, key, None)
            if col is not None:
                o.append(col.asc())
            else:
                logger.warning(
                    "Sort field '%s' not found on model '%s', ignored",
                    key,
                    model.__name__,
                )
    return o


def _get_column_map[T: Model](model: type[T]) -> dict[str, Any]:
    """获取模型可用的数据库列映射。

    Args:
        model: ORM 模型类 / ORM model class.

    Returns:
        列名到列对象的映射 / Column-name to column-object map.

    Raises:
        无 / None.
    """
    try:
        mapper = inspect(model)
        return {c.key: getattr(model, c.key) for c in mapper.columns}
    except (AttributeError, SQLAlchemyError, TypeError):
        logger.debug(
            "Cannot inspect columns for model %s; falling back to class attributes",
            model.__name__,
        )

    annotations = getattr(model, "__annotations__", {})
    return {
        name: getattr(model, name)
        for name in annotations
        if not name.startswith("_") and hasattr(model, name)
    }


def _get_column_names[T: Model](model: type[T]) -> set[str]:
    """获取模型可用的数据库列名集合。"""
    return set(_get_column_map(model))


def _combined_conditions[T: Model](
    model: type[T],
    filters: dict[str, Any] | None,
    conditions: Sequence[ColumnElement[bool]] | None = None,
    *,
    require_non_empty: bool,
) -> list[ColumnElement[bool]]:
    """合并字典筛选条件和直接传入的 SQLAlchemy 条件。"""
    combined = _conds(model, filters)
    if conditions:
        combined.extend(conditions)
    if require_non_empty and not combined:
        raise ValueError(f"At least one condition is required for {model.__name__}")
    return combined


def _validate_column_values[T: Model](
    model: type[T],
    values: dict[str, Any],
) -> dict[str, Any]:
    """校验待写入字段均为模型列。"""
    columns = _get_column_map(model)
    for key in values:
        if key not in columns:
            raise ValueError(f"Unknown column '{key}' for model '{model.__name__}'")
    return dict(values)


async def _retry_create_after_conflict[T: Model](
    s: AsyncSession,
    stmt: Select[tuple[T]],
    model: type[T],
    data: dict[str, Any],
) -> tuple[T, bool]:
    """在唯一约束冲突后再尝试创建一次。

    Args:
        s: 异步会话 / Async session.
        stmt: 用于回查现有记录的查询语句 / Query statement for lookup.
        model: ORM 模型类 / ORM model class.
        data: 待创建字段 / Fields used to build the record.

    Returns:
        (对象, 是否新建) / (object, whether newly created).

    Raises:
        DatabaseError: 重试仍失败或出现外键冲突时 / On retry failure or FK violation.
    """
    logger.warning(
        "Unique constraint conflict but no existing record found; "
        "retrying create once (possible concurrent rollback)"
    )
    try:
        obj = model(**data)
        s.add(obj)
        await s.commit()
        await s.refresh(obj)
    except IntegrityError as e2:
        await s.rollback()
        if _is_fk_constraint_violation(e2):
            raise DatabaseError("Foreign key violation on retry") from e2
        try:
            res2 = await s.execute(stmt)
            existing2 = res2.scalar_one_or_none()
        except SQLAlchemyError as e3:
            raise DatabaseError("Query failed after second unique conflict") from e3
        if existing2 is None:
            raise DatabaseError(
                "Data inconsistency: unique conflict twice, no record found"
            ) from e2
        return existing2, False
    except SQLAlchemyError as e2:
        await s.rollback()
        raise DatabaseError("Retry create failed") from e2
    else:
        return obj, True


async def _create_with_retry[T: Model](
    s: AsyncSession,
    stmt: Select[tuple[T]],
    model: type[T],
    data: dict[str, Any],
) -> tuple[T, bool]:
    """创建记录，并在唯一约束冲突时回查或重试。

    Args:
        s: 异步会话 / Async session.
        stmt: 用于回查现有记录的查询语句 / Query statement for lookup.
        model: ORM 模型类 / ORM model class.
        data: 待创建字段 / Fields used to build the record.

    Returns:
        (对象, 是否新建) / (object, whether newly created).

    Raises:
        DatabaseError: 创建、回查或重试过程中发生数据库错误时。
    """
    obj = model(**data)
    s.add(obj)

    try:
        await s.commit()
        await s.refresh(obj)
    except IntegrityError as e:
        await s.rollback()
        if _is_fk_constraint_violation(e):
            raise DatabaseError("Foreign key violation during insert") from e
        try:
            res = await s.execute(stmt)
            existing = res.scalar_one_or_none()
        except SQLAlchemyError as e2:
            raise DatabaseError("Query failed after unique constraint conflict") from e2
        if existing is None:
            return await _retry_create_after_conflict(s, stmt, model, data)
        logger.warning(
            "Unique constraint conflict resolved for %s, returned existing record",
            model.__name__,
        )
        return existing, False
    except SQLAlchemyError as e:
        await s.rollback()
        raise DatabaseError("Failed to create record") from e
    else:
        return obj, True


async def _update_existing[T: Model](
    s: AsyncSession,
    model: type[T],
    cs: list[ColumnElement[bool]],
    obj: T,
    update_values: dict[str, Any],
) -> T:
    """就地更新已有记录。

    Args:
        s: 异步会话 / Async session.
        model: ORM 模型类 / ORM model class.
        cs: 预生成的筛选条件 / Prebuilt filter conditions.
        obj: 需要刷新的对象 / Object to refresh after update.
        update_values: 更新字段 / Fields to update.

    Returns:
        更新后的对象；若没有更新内容则直接返回原对象 / Updated object.

    Raises:
        DatabaseError: 更新失败时 / On update failure.
    """
    if not update_values:
        return obj

    stmt_update = sqlalchemy_update(model)
    stmt_update = stmt_update.where(*cs).values(**update_values)

    try:
        await s.execute(stmt_update)
        await s.commit()
        await s.refresh(obj)
    except SQLAlchemyError as e:
        await s.rollback()
        raise DatabaseError("Failed to update record") from e

    return obj


async def create[T: Model](model: type[T], **fields: Any) -> T:
    """创建一条新记录。

    Args:
        model: ORM 模型类 / ORM model class.
        fields: 用于实例化模型的字段 / Fields used to instantiate the model.

    Returns:
        新创建并刷新后的模型对象 / Newly created and refreshed model object.

    Raises:
        DatabaseError: 创建或刷新失败时 / On create or refresh failure.
    """
    fields = _validate_column_values(model, fields)
    async with get_session() as s:
        obj = model(**fields)
        s.add(obj)
        try:
            await s.commit()
            await s.refresh(obj)
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Failed to create record") from e
        return obj


async def get_one[T: Model](
    model: type[T],
    filters: dict[str, Any],
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
) -> T | None:
    """获取符合条件的单条记录。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.

    Returns:
        匹配对象或 None / Matching object or None.

    Raises:
        DatabaseError: 查询失败时 / On query failure.
    """
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=True,
    )
    async with get_session() as s:
        try:
            stmt = select(model)
            stmt = stmt.where(*cs)
            stmt = stmt.limit(1)
            res = await s.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError("Failed to query record") from e


async def get_or_create[T: Model](
    model: type[T],
    defaults: dict[str, Any] | None = None,
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
    **filters: Any,
) -> tuple[T, bool]:
    """获取一条记录，不存在则创建。

    Args:
        model: ORM 模型类 / ORM model class.
        defaults: 创建时补充使用的字段 / Extra fields used when creating.
        filters: 用于查找已有记录的字段 / Lookup fields.

    Returns:
        (对象, 是否新建) / (object, whether newly created).

    Raises:
        DatabaseError: 查询、创建或重试失败时 / On query, create, or retry failure.
    """
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=True,
    )
    async with get_session() as s:
        stmt = select(model)
        stmt = stmt.where(*cs)
        stmt = stmt.limit(1)
        try:
            res = await s.execute(stmt)
            obj = res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError("Query failed in get_or_create") from e

        if obj is not None:
            return obj, False

        data = dict(filters)
        if defaults:
            data.update(defaults)
        data = _validate_column_values(model, data)
        return await _create_with_retry(s, stmt, model, data)


async def update_or_create[T: Model](
    model: type[T],
    filters: dict[str, Any],
    defaults: dict[str, Any] | None = None,
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
) -> tuple[T, bool]:
    """先更新，找不到则创建。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 查找已有记录的条件 / Conditions for locating the record.
        defaults: 找到记录时用于更新的字段，未找到时用于创建的字段。

    Returns:
        (对象, 是否新建) / (object, whether newly created).

    Raises:
        DatabaseError: 查询、更新、创建或刷新失败时。

    Notes:
        该操作不是原子 upsert，并发写入可能产生丢失更新。
        This operation is not an atomic upsert; concurrent writes may lose updates.
    """
    logger.debug(
        "update_or_create called for %s (not atomic; concurrent writes may cause "
        "lost updates). filters=%s",
        model.__name__,
        filters,
    )
    now = time.monotonic()
    if now - _last_warn_time.get(model.__name__, 0) >= _WARN_INTERVAL:
        logger.warning(
            "update_or_create non-atomic usage for %s (this warning is throttled "
            "to once per %ds per model)",
            model.__name__,
            _WARN_INTERVAL,
        )
        _last_warn_time[model.__name__] = now
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=True,
    )
    async with get_session() as s:
        stmt = select(model)
        stmt = stmt.where(*cs)
        stmt = stmt.limit(1)
        try:
            res = await s.execute(stmt)
            obj = res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError("Query failed in update_or_create") from e

        if obj is not None:
            update_values = _validate_column_values(model, defaults or {})
            updated = await _update_existing(s, model, cs, obj, update_values)
            return updated, False

        data = dict(filters)
        if defaults:
            data.update(defaults)
        data = _validate_column_values(model, data)
        return await _create_with_retry(s, stmt, model, data)


async def update[T: Model](
    model: type[T],
    filters: dict[str, Any],
    values: dict[str, Any],
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
) -> tuple[int, bool]:
    """更新符合条件的记录。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.
        values: 要更新的字段和值 / Fields and values to update.

    Returns:
        (受影响的行数, 行数是否已知) / (affected rows, whether rowcount is known).
        当行数未知时，第一个元素为 ROWCOUNT_UNKNOWN。

    Raises:
        DatabaseError: 更新失败时 / On update failure.
    """
    if not values:
        return (0, True)

    update_values = _validate_column_values(model, values)
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=True,
    )
    async with get_session() as s:
        stmt = sqlalchemy_update(model)
        stmt = stmt.where(*cs).values(**update_values)

        try:
            result = await s.execute(stmt)
            await s.commit()
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Failed to update records") from e
        else:
            rc = getattr(result, "rowcount", None)
            return (int(rc), True) if rc is not None else (ROWCOUNT_UNKNOWN, False)


async def delete[T: Model](
    model: type[T],
    filters: dict[str, Any],
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
) -> tuple[int, bool]:
    """删除符合条件的记录。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 删除条件 / Delete conditions.

    Returns:
        (受影响的行数, 行数是否已知) / (affected rows, whether rowcount is known).
        当行数未知时，第一个元素为 ROWCOUNT_UNKNOWN。

    Raises:
        DatabaseError: 删除失败时 / On delete failure.
    """
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=True,
    )
    async with get_session() as s:
        stmt = sqlalchemy_delete(model)
        stmt = stmt.where(*cs)

        try:
            result = await s.execute(stmt)
            await s.commit()
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Failed to delete records") from e
        else:
            rc = getattr(result, "rowcount", None)
            return (int(rc), True) if rc is not None else (ROWCOUNT_UNKNOWN, False)


async def exists[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
) -> bool:
    """判断是否存在符合条件的记录。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 判断条件 / Existence check conditions.

    Returns:
        存在返回 True，不存在返回 False / True if a match exists, else False.

    Raises:
        DatabaseError: 判断失败时 / On existence check failure.
    """
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=False,
    )
    async with get_session() as s:
        try:
            stmt = select(1).select_from(model)
            if cs:
                stmt = stmt.where(*cs)
            stmt = stmt.limit(1)
            res = await s.execute(stmt)
            return res.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            raise DatabaseError("Failed to check existence") from e


async def bulk_create[T: Model](
    model: type[T],
    objs: list[dict[str, Any]],
    *,
    commit: bool = True,
    partial: bool = False,
) -> tuple[list[T], list[tuple[int, str]]]:
    """批量创建多条记录。

    Args:
        model: ORM 模型类 / ORM model class.
        objs: 待创建字段字典列表 / List of field dictionaries.
        commit: 是否立即提交 / Whether to commit immediately.
        partial: 是否允许部分成功 / Whether to skip failed rows and continue.

    Returns:
        (成功对象列表, 失败项列表) / (created objects, failure list).

    Raises:
        DatabaseError: partial 为 False 且批量创建失败时。
    """
    validated_objs = [_validate_column_values(model, fields) for fields in objs]
    async with get_session() as s:
        if not partial:
            instances = [model(**fields) for fields in validated_objs]
            s.add_all(instances)
            try:
                if commit:
                    await s.commit()
                    for obj in instances:
                        await s.refresh(obj)
                else:
                    await s.flush()
            except SQLAlchemyError as e:
                await s.rollback()
                raise DatabaseError("Bulk create failed") from e
            return instances, []

        # Partial mode: individual savepoints
        created: list[T] = []
        failed: list[tuple[int, str]] = []
        for idx, fields in enumerate(validated_objs):
            savepoint = await s.begin_nested()
            try:
                obj = model(**fields)
                s.add(obj)
                await savepoint.commit()
                created.append(obj)
            except SQLAlchemyError as exc:
                await savepoint.rollback()
                msg = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Skipped item %d in bulk_create (partial=True): %s", idx, msg
                )
                failed.append((idx, msg))
        try:
            if commit:
                await s.commit()
                for obj in created:
                    await s.refresh(obj)
            else:
                await s.flush()
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Bulk create failed") from e
        return created, failed


def _get_session_dialect_name(s: AsyncSession) -> str:
    """获取当前会话绑定的数据库方言名称。"""
    bind = s.get_bind()
    return str(bind.dialect.name)


def _validate_upsert_conflict_target[T: Model](
    model: type[T],
    columns: dict[str, Any],
    conflict_fields: Sequence[str] | None,
    constraint: str | None,
) -> list[str]:
    """校验 upsert 冲突目标并返回字段列表。"""
    if conflict_fields and constraint:
        raise ValueError("Specify either conflict_fields or constraint, not both")
    if not conflict_fields and not constraint:
        raise ValueError("An upsert conflict target is required")

    conflict_keys = list(conflict_fields or [])
    for key in conflict_keys:
        if key not in columns:
            raise ValueError(f"Unknown column '{key}' for model '{model.__name__}'")
    return conflict_keys


def _prepare_upsert_update_values[T: Model](
    model: type[T],
    insert_values: dict[str, Any],
    conflict_keys: Sequence[str],
    update_values: dict[str, Any] | None,
) -> tuple[list[str], dict[str, Any] | None]:
    """准备 upsert 的更新字段。"""
    if update_values is not None:
        explicit_update_values = _validate_column_values(model, update_values)
        if not explicit_update_values:
            raise ValueError("At least one update column is required for upsert")
        return [], explicit_update_values

    update_keys = [key for key in insert_values if key not in conflict_keys]
    if not update_keys:
        raise ValueError("At least one update column is required for upsert")
    return update_keys, None


def _dialect_insert_statement[T: Model](
    model: type[T],
    dialect_name: str,
    constraint: str | None,
) -> Any:
    """按数据库方言创建 upsert insert 语句。"""
    if dialect_name == "sqlite":
        if constraint is not None:
            raise ValueError("SQLite upsert requires conflict_fields")
        return sqlite_insert(model)
    if dialect_name == "postgresql":
        return postgresql_insert(model)
    raise DatabaseError(f"Upsert is not supported for dialect '{dialect_name}'")


def _upsert_set_values(
    stmt: Any,
    update_keys: Sequence[str],
    explicit_update_values: dict[str, Any] | None,
) -> dict[str, Any]:
    """生成 upsert 的 SET 字段。"""
    if explicit_update_values is not None:
        return explicit_update_values
    return {key: getattr(stmt.excluded, key) for key in update_keys}


def _upsert_conflict_kwargs(
    columns: dict[str, Any],
    conflict_keys: Sequence[str],
    constraint: str | None,
) -> dict[str, Any]:
    """生成 on_conflict_do_update 的冲突目标参数。"""
    if constraint is not None:
        return {"constraint": constraint}
    return {"index_elements": [columns[key] for key in conflict_keys]}


def _mysql_upsert_set_values(
    stmt: Any,
    update_keys: Sequence[str],
    explicit_update_values: dict[str, Any] | None,
) -> dict[str, Any]:
    """生成 MySQL on_duplicate_key_update 的 SET 字段。

    MySQL 使用 ``stmt.inserted.<col>`` 引用 INSERT 的值，
    等价于 PostgreSQL/SQLite 的 ``stmt.excluded.<col>``。
    """
    if explicit_update_values is not None:
        return explicit_update_values
    return {key: getattr(stmt.inserted, key) for key in update_keys}


async def upsert[T: Model](
    model: type[T],
    insert_values: dict[str, Any],
    *,
    conflict_fields: Sequence[str] | None = None,
    constraint: str | None = None,
    update_values: dict[str, Any] | None = None,
) -> T:
    """执行方言级原子 upsert（SQLite/PostgreSQL/MySQL）。

    Args:
        model: ORM 模型类 / ORM model class.
        insert_values: 插入字段 / Values used for INSERT.
        conflict_fields: 唯一冲突字段 / Conflict-target columns.
        constraint: PostgreSQL 约束名 / PostgreSQL constraint name.
        update_values: 冲突时更新字段；默认使用 excluded insert values。

    Returns:
        upsert 后返回的 ORM 对象 / ORM object returned by RETURNING.

    Raises:
        ValueError: 参数或字段非法时 / On invalid arguments or columns.
        DatabaseError: 数据库执行失败或方言不支持时 / On DB failure.
    """
    if not insert_values:
        raise ValueError("insert_values cannot be empty")

    insert_values = _validate_column_values(model, insert_values)
    columns = _get_column_map(model)
    conflict_keys = _validate_upsert_conflict_target(
        model,
        columns,
        conflict_fields,
        constraint,
    )
    update_keys, explicit_update_values = _prepare_upsert_update_values(
        model,
        insert_values,
        conflict_keys,
        update_values,
    )

    async with get_session() as s:
        dialect_name = _get_session_dialect_name(s)

        if dialect_name == "mysql":
            return await _mysql_upsert(
                s,
                model,
                insert_values,
                columns,
                conflict_keys,
                update_keys,
                explicit_update_values,
                constraint,
            )

        insert_stmt = _dialect_insert_statement(model, dialect_name, constraint)
        stmt = insert_stmt.values(**insert_values)
        set_values = _upsert_set_values(stmt, update_keys, explicit_update_values)
        conflict_kwargs = _upsert_conflict_kwargs(columns, conflict_keys, constraint)

        stmt = stmt.on_conflict_do_update(**conflict_kwargs, set_=set_values)
        stmt = stmt.returning(model)

        try:
            result = await s.execute(stmt)
            obj = result.scalar_one()
            await s.commit()
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Upsert failed") from e
        return obj


async def _mysql_upsert[T: Model](  # noqa: PLR0913
    s: AsyncSession,
    model: type[T],
    insert_values: dict[str, Any],
    columns: dict[str, Any],
    conflict_keys: list[str],
    update_keys: list[str],
    explicit_update_values: dict[str, Any] | None,
    constraint: str | None,
) -> T:
    """MySQL 方言的 upsert 实现。

    使用 ``INSERT ... ON DUPLICATE KEY UPDATE`` 语义。MySQL 不支持
    ``RETURNING``，因此执行后通过 ``conflict_fields`` 做一次 follow-up
    ``SELECT`` 取回最新行。
    """
    if constraint is not None:
        raise ValueError(
            "MySQL upsert does not support constraint; use conflict_fields"
        )
    if not conflict_keys:
        raise ValueError("MySQL upsert requires conflict_fields for follow-up SELECT")

    insert_stmt = mysql_insert(model).values(**insert_values)
    set_values = _mysql_upsert_set_values(
        insert_stmt, update_keys, explicit_update_values
    )
    stmt = insert_stmt.on_duplicate_key_update(**set_values)

    try:
        await s.execute(stmt)
        await s.commit()
    except SQLAlchemyError as e:
        await s.rollback()
        raise DatabaseError("Upsert failed") from e

    # MySQL 不支持 RETURNING，通过 conflict_keys 做一次 SELECT 取回最新行。
    where_clauses = [
        columns[key].is_(insert_values[key])
        if insert_values[key] is None
        else columns[key] == insert_values[key]
        for key in conflict_keys
    ]
    try:
        result = await s.execute(select(model).where(*where_clauses))
        obj = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        raise DatabaseError("Upsert failed to fetch row") from e
    if obj is None:
        raise DatabaseError("Upsert succeeded but row not found")
    return obj


async def list_items[T: Model](  # noqa: PLR0913
    model: type[T],
    filters: dict[str, Any] | None = None,
    order_by: Sequence[str] | None = None,
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[T]:
    """列出符合条件的记录。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.
        order_by: 排序字段 / Sort fields.
        offset: 偏移量 / Result offset.
        limit: 限制数量 / Maximum number of rows.

    Returns:
        模型对象列表 / List of model objects.

    Raises:
        DatabaseError: 查询失败时 / On query failure.
    """
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=False,
    )
    async with get_session() as s:
        try:
            stmt = select(model)
            if cs:
                stmt = stmt.where(*cs)
            os = _orders(model, order_by)
            if os:
                stmt = stmt.order_by(*os)
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            res = await s.execute(stmt)
            return list(res.scalars().all())
        except SQLAlchemyError as e:
            raise DatabaseError("Failed to list records") from e


async def async_iterate_safe[T: Model](  # noqa: PLR0913
    model: type[T],
    *,
    filters: dict[str, Any] | None = None,
    conditions: Sequence[ColumnElement[bool]] | None = None,
    order_by: Sequence[str] | None = None,
    batch_size: int = 1000,
    callback: Callable[[T], Awaitable[None]] | None = None,
    collect: bool = False,
) -> list[T]:
    """安全遍历大型结果集。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.
        order_by: 排序字段列表 / Sort field list.
        batch_size: 每批加载的记录数 / Rows fetched per batch.
        callback: 对每条记录调用的异步回调 / Async callback per item.
        collect: 是否把所有结果收集后返回 / Whether to collect all items.

    Returns:
        若 collect 为 True，则返回收集到的对象列表，否则返回空列表。
        Returns the collected objects when collect is True, otherwise an empty list.

    Raises:
        ValueError: callback 与 collect 同时启用时 / When callback and collect
            are both set.
        DatabaseError: 迭代查询失败时 / On iteration query failure.
    """
    if callback is not None and collect:
        raise ValueError("callback and collect are mutually exclusive")

    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=False,
    )
    results: list[T] = []
    async with get_session() as s:
        try:
            stmt = select(model)
            if cs:
                stmt = stmt.where(*cs)
            os = _orders(model, order_by)
            if os:
                stmt = stmt.order_by(*os)
            stream = await s.stream(stmt, execution_options={"yield_per": batch_size})
            async for row in stream:
                item = row[0]
                if callback is not None:
                    await callback(item)
                if collect:
                    results.append(item)
        except SQLAlchemyError as e:
            raise DatabaseError("Failed to iterate records") from e
    return results


async def count[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    *,
    conditions: Sequence[ColumnElement[bool]] | None = None,
) -> int:
    """统计符合条件的记录数量。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.

    Returns:
        记录数量 / Number of matching records.

    Raises:
        DatabaseError: 统计失败时 / On count failure.
    """
    cs = _combined_conditions(
        model,
        filters,
        conditions,
        require_non_empty=False,
    )
    async with get_session() as s:
        try:
            stmt = select(func.count("*")).select_from(model)
            if cs:
                stmt = stmt.where(*cs)
            res = await s.execute(stmt)
            return int(res.scalar_one())
        except SQLAlchemyError as e:
            raise DatabaseError("Failed to count records") from e
