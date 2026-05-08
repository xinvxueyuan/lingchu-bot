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
import warnings
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any

from nonebot_plugin_orm import Model, get_session
from sqlalchemy import Select, func, select
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy import update as sqlalchemy_update
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
        无 / None.
    """
    if not filters:
        return []
    c: list[ColumnElement[bool]] = []
    for k, v in filters.items():
        col = getattr(model, k, None)
        if col is None:
            logger.warning(
                "Filter column '%s' not found on model '%s', ignored",
                k,
                model.__name__,
            )
            continue
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


def _get_column_names[T: Model](model: type[T]) -> set[str] | None:
    """获取模型可用的数据库列名集合。

    Args:
        model: ORM 模型类 / ORM model class.

    Returns:
        列名集合；无法反射时返回 None / Column-name set or None.

    Raises:
        无 / None.
    """
    try:
        mapper = inspect(model)
        return {c.key for c in mapper.columns}
    except (SQLAlchemyError, TypeError):
        logger.warning("Cannot inspect columns for model %s", model.__name__)
        return None


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
    if cs:
        stmt_update = stmt_update.where(*cs)
    stmt_update = stmt_update.values(**update_values)

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


async def get_one[T: Model](model: type[T], filters: dict[str, Any]) -> T | None:
    """获取符合条件的单条记录。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.

    Returns:
        匹配对象或 None / Matching object or None.

    Raises:
        DatabaseError: 查询失败时 / On query failure.
    """
    async with get_session() as s:
        try:
            stmt = select(model)
            cs = _conds(model, filters)
            if cs:
                stmt = stmt.where(*cs)
            stmt = stmt.limit(1)
            res = await s.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError("Failed to query record") from e


async def get_or_create[T: Model](
    model: type[T],
    defaults: dict[str, Any] | None = None,
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
    async with get_session() as s:
        stmt = select(model)
        cs = _conds(model, filters)
        if cs:
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
        return await _create_with_retry(s, stmt, model, data)


async def update_or_create[T: Model](
    model: type[T],
    filters: dict[str, Any],
    defaults: dict[str, Any] | None = None,
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
    async with get_session() as s:
        cs = _conds(model, filters)
        stmt = select(model)
        if cs:
            stmt = stmt.where(*cs)
        stmt = stmt.limit(1)
        try:
            res = await s.execute(stmt)
            obj = res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseError("Query failed in update_or_create") from e

        if obj is not None:
            updated = await _update_existing(s, model, cs, obj, defaults or {})
            return updated, False

        data = dict(filters)
        if defaults:
            data.update(defaults)
        return await _create_with_retry(s, stmt, model, data)


async def update[T: Model](
    model: type[T],
    filters: dict[str, Any],
    values: dict[str, Any],
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
    async with get_session() as s:
        valid_columns = _get_column_names(model)
        if valid_columns is not None:
            update_values = {}
            for k, v in values.items():
                if k in valid_columns:
                    update_values[k] = v
                else:
                    logger.warning(
                        "Field '%s' is not a valid DB column for model '%s', ignored",
                        k,
                        model.__name__,
                    )
        else:
            logger.warning(
                "Cannot determine columns for '%s', skipping field validation. "
                "Invalid fields may cause DB errors.",
                model.__name__,
            )
            update_values = values

        if not update_values:
            return (0, True)

        stmt = sqlalchemy_update(model)
        cs = _conds(model, filters)
        if cs:
            stmt = stmt.where(*cs)
        stmt = stmt.values(**update_values)

        try:
            result = await s.execute(stmt)
            await s.commit()
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Failed to update records") from e
        else:
            rc = getattr(result, "rowcount", None)
            return (int(rc), True) if rc is not None else (ROWCOUNT_UNKNOWN, False)


async def delete[T: Model](model: type[T], filters: dict[str, Any]) -> tuple[int, bool]:
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
    async with get_session() as s:
        stmt = sqlalchemy_delete(model)
        cs = _conds(model, filters)
        if cs:
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


async def exists[T: Model](model: type[T], filters: dict[str, Any]) -> bool:
    """判断是否存在符合条件的记录。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 判断条件 / Existence check conditions.

    Returns:
        存在返回 True，不存在返回 False / True if a match exists, else False.

    Raises:
        DatabaseError: 判断失败时 / On existence check failure.
    """
    async with get_session() as s:
        try:
            stmt = select(1).select_from(model)
            cs = _conds(model, filters)
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
    async with get_session() as s:
        if not partial:
            instances = [model(**fields) for fields in objs]
            s.add_all(instances)
            if commit:
                try:
                    await s.commit()
                    for obj in instances:
                        await s.refresh(obj)
                except SQLAlchemyError as e:
                    await s.rollback()
                    raise DatabaseError("Bulk create failed") from e
            return instances, []

        # Partial mode: individual savepoints
        created: list[T] = []
        failed: list[tuple[int, str]] = []
        for idx, fields in enumerate(objs):
            savepoint = await s.begin_nested()
            try:
                obj = model(**fields)
                s.add(obj)
                await savepoint.commit()
                if commit:
                    await s.refresh(obj)
                created.append(obj)
            except SQLAlchemyError as exc:
                await savepoint.rollback()
                msg = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Skipped item %d in bulk_create (partial=True): %s", idx, msg
                )
                failed.append((idx, msg))
        return created, failed


async def list_items[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    order_by: Sequence[str] | None = None,
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
    async with get_session() as s:
        try:
            stmt = select(model)
            cs = _conds(model, filters)
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


async def async_iterate[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    order_by: Sequence[str] | None = None,
    batch_size: int = 1000,
) -> AsyncGenerator[T]:
    """迭代大型结果集。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.
        order_by: 排序字段 / Sort fields.
        batch_size: 每批拉取的行数 / Rows fetched per batch.

    Returns:
        逐条产出的模型对象生成器 / Async generator yielding model objects.

    Raises:
        无 / None.

    Notes:
        该函数已弃用，推荐使用 async_iterate_safe。
        The function is deprecated; use async_iterate_safe instead.
        会话会在生成器生命周期内保持打开，提前退出时需要显式关闭。
    """
    warnings.warn(
        "async_iterate is deprecated; use async_iterate_safe instead",
        DeprecationWarning,
        stacklevel=2,
    )
    async with get_session() as s:
        try:
            stmt = select(model)
            cs = _conds(model, filters)
            if cs:
                stmt = stmt.where(*cs)
            os = _orders(model, order_by)
            if os:
                stmt = stmt.order_by(*os)
            result = await s.stream(stmt, execution_options={"yield_per": batch_size})
            async for row in result:
                yield row[0]
        except SQLAlchemyError:
            logger.exception("Async iteration failed")
            return


async def async_iterate_safe[T: Model](  # noqa: PLR0913
    model: type[T],
    *,
    filters: dict[str, Any] | None = None,
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

    results: list[T] = []
    async with get_session() as s:
        try:
            stmt = select(model)
            cs = _conds(model, filters)
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


async def count[T: Model](model: type[T], filters: dict[str, Any] | None = None) -> int:
    """统计符合条件的记录数量。

    Args:
        model: ORM 模型类 / ORM model class.
        filters: 筛选条件 / Filter conditions.

    Returns:
        记录数量 / Number of matching records.

    Raises:
        DatabaseError: 统计失败时 / On count failure.
    """
    async with get_session() as s:
        try:
            stmt = select(func.count("*")).select_from(model)
            cs = _conds(model, filters)
            if cs:
                stmt = stmt.where(*cs)
            res = await s.execute(stmt)
            return int(res.scalar_one())
        except SQLAlchemyError as e:
            raise DatabaseError("Failed to count records") from e
