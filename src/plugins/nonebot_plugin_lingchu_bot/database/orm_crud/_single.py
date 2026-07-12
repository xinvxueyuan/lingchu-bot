"""单条记录 CRUD 操作：create、get_one、update、delete、exists、count 等。"""

from __future__ import annotations

from collections.abc import Sequence
import time
from typing import TYPE_CHECKING, Any

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model, get_session
from sqlalchemy import (
    Select,
    delete as sqlalchemy_delete,
    func,
    select,
    update as sqlalchemy_update,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ._base import (
    _WARN_INTERVAL,
    ROWCOUNT_UNKNOWN,
    DatabaseError,
    _combined_conditions,
    _is_fk_constraint_violation,
    _last_warn_time,
    _validate_column_values,
    logger,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.elements import ColumnElement


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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.

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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.

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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.

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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.

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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.

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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.

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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.

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
