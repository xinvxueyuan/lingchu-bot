"""
数据库CRUD函数（全异步 / 非阻塞）
提供通用的ORM模型的增删查改（CRUD）操作，基于SQLAlchemy异步引擎和nonebot_plugin_orm。

所有操作在成功时直接返回结果，失败时抛出 DatabaseError。
查询类函数用 None / 空列表 表示"未找到"，与"数据库异常"（抛出异常）明确分开。
"""

# ruff: noqa: TRY003 — DatabaseError 是通用异常类，消息在每次抛出时提供

from nonebot import require

require("nonebot_plugin_orm")
import logging
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Any, cast

from nonebot_plugin_orm import Model, get_session
from sqlalchemy import Select, func, select
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult

logger = logging.getLogger(__name__)
ROWCOUNT_UNKNOWN = -1


class DatabaseError(Exception):
    """数据库操作失败时抛出的基础异常。"""


def _is_fk_constraint_violation(e: IntegrityError) -> bool:
    """检测 IntegrityError 是否为外键约束冲突（而非唯一约束冲突）。"""
    msg = str(e.orig).lower()
    return "foreign key" in msg


def _conds[T: Model](
    model: type[T],
    filters: dict[str, Any] | None,
) -> list[ColumnElement[bool]]:
    """构造SQLAlchemy的条件表达式列表。"""
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
    """构造SQLAlchemy的排序表达式列表。"""  # no change in logic
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
    """获取模型的所有数据库列名。失败时返回 None。"""
    try:
        mapper = inspect(model)
        return {c.key for c in mapper.columns}
    except (SQLAlchemyError, TypeError):
        logger.warning("Cannot inspect columns for model %s", model.__name__)
        return None


async def _create_with_retry[T: Model](
    s: AsyncSession,
    stmt: Select[tuple[T]],
    model: type[T],
    data: dict[str, Any],
) -> tuple[T, bool]:
    """创建记录，唯一约束冲突时重试查询。返回 (对象, 是否新建)。"""
    obj = model(**data)
    s.add(obj)

    try:
        await s.commit()
        await s.refresh(obj)
    except IntegrityError as e:
        await s.rollback()
        if _is_fk_constraint_violation(e):
            raise DatabaseError("Foreign key violation during insert") from e
        # Unique constraint conflict — retrieve existing record
        try:
            res = await s.execute(stmt)
            existing = res.scalar_one_or_none()
        except SQLAlchemyError as e2:
            raise DatabaseError("Query failed after unique constraint conflict") from e2
        if existing is None:
            raise DatabaseError(
                "Data inconsistency: unique constraint conflict but no existing record"
            ) from e
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
    """就地更新已有记录。无更新值时直接返回原对象。"""
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


# ----------------- 单条操作 -----------------


async def create[T: Model](model: type[T], **fields: Any) -> T:
    """异步创建一条新记录。
    返回：新创建的模型对象。
    抛出：DatabaseError。
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
    """异步获取符合条件的单条记录。
    返回：模型对象 或 None（无匹配记录）。
    抛出：DatabaseError。
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
    """异步获取或创建一条记录。
    返回：(对象, 是否新建)。
    抛出：DatabaseError。
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
    """异步更新或创建一条记录。
    注意：本操作不是原子 upsert，并发写入可能出现更新丢失。
    返回：(对象, 是否新建)。
    抛出：DatabaseError。
    """
    logger.warning(
        "update_or_create is not atomic: concurrent writes may cause lost updates. "
        "Called for %s with filters=%s",
        model.__name__,
        filters,
    )
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
) -> int:
    """异步更新符合条件的记录。
    参数：
        model: ORM模型类
        filters: 筛选条件
        values: 要更新的字段及其值
    返回：
        受影响的行数。可能返回 -1（ROWCOUNT_UNKNOWN），表示驱动未报告行数，
        调用方应将 -1 视为"成功但行数未知"。
    抛出：DatabaseError。
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
            return 0

        stmt = sqlalchemy_update(model)
        cs = _conds(model, filters)
        if cs:
            stmt = stmt.where(*cs)
        stmt = stmt.values(**update_values)

        try:
            result = cast("CursorResult[Any]", await s.execute(stmt))
            await s.commit()
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Failed to update records") from e
        else:
            rc = result.rowcount
            return int(rc) if rc is not None else ROWCOUNT_UNKNOWN


async def delete[T: Model](model: type[T], filters: dict[str, Any]) -> int:
    """异步删除符合条件的记录。
    返回：受影响的行数（-1 表示行数未知）。
    抛出：DatabaseError。
    """
    async with get_session() as s:
        stmt = sqlalchemy_delete(model)
        cs = _conds(model, filters)
        if cs:
            stmt = stmt.where(*cs)

        try:
            result = cast("CursorResult[Any]", await s.execute(stmt))
            await s.commit()
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Failed to delete records") from e
        else:
            rc = result.rowcount
            return int(rc) if rc is not None else ROWCOUNT_UNKNOWN


async def exists[T: Model](model: type[T], filters: dict[str, Any]) -> bool:
    """异步判断是否存在符合条件的记录。
    返回：True=存在，False=不存在。
    抛出：DatabaseError。
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


# ----------------- 批量操作 -----------------


async def bulk_create[T: Model](
    model: type[T],
    objs: list[dict[str, Any]],
    *,
    commit: bool = True,
    partial: bool = False,
) -> list[T]:
    """异步批量创建多条记录。
    参数：
        model: ORM模型类
        objs: 字段字典列表
        commit: 是否立即提交。若为 False，返回的实例未持久化且缺少数据库生成的值。
        partial: 若为 True，单条插入失败时跳过并记录警告，返回成功创建的列表。
                 若为 False（默认），任何失败抛出 DatabaseError。
    返回：新创建的模型对象列表。
    抛出：DatabaseError（partial=False 时）。
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
            return instances

        # Partial mode: individual savepoints
        created: list[T] = []
        for idx, fields in enumerate(objs):
            savepoint = await s.begin_nested()
            try:
                obj = model(**fields)
                s.add(obj)
                await savepoint.commit()
                if commit:
                    await s.refresh(obj)
                created.append(obj)
            except SQLAlchemyError:
                await savepoint.rollback()
                logger.warning("Skipped item %d in bulk_create (partial=True)", idx)
        return created


async def list_items[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    order_by: Sequence[str] | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[T]:
    """异步获取符合条件的多条记录列表（一次性加载至内存）。
    返回：模型对象列表。
    抛出：DatabaseError。
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
    """异步迭代大型结果集，避免一次性加载所有记录导致内存压力。
    注意：数据库会话在生成器生命周期内保持打开。如果提前退出循环，
    应显式关闭生成器（await gen.aclose() 或 contextlib.aclosing），
    否则会话会延迟到生成器被垃圾回收时才释放。
    出错时生成器静默结束。
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
            result = await s.stream(stmt, execution_options={"yield_per": batch_size})
            async for row in result:
                yield row[0]
        except SQLAlchemyError:
            logger.exception("Async iteration failed")
            return


async def count[T: Model](model: type[T], filters: dict[str, Any] | None = None) -> int:
    """异步统计符合条件的记录数量。
    返回：记录数。
    抛出：DatabaseError。
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
