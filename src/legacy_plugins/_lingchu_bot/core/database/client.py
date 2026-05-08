"""
数据库CRUD函数（全异步 / 非阻塞）
提供通用的ORM模型的增删查改（CRUD）操作，基于SQLAlchemy异步引擎和nonebot_plugin_orm。

所有操作均返回 (结果, 状态) 或 (结果, 新建, 状态) 等元组：
- 状态（bool）：True 表示操作成功，False 表示失败或异常。
- 新建（bool）：部分函数用于区分是否新建（如 get_or_create, update_or_create）。

本模块所有公开函数均为 async 函数，内部仅使用非阻塞 I/O，适合高并发异步应用。
"""

from nonebot import require

require("nonebot_plugin_orm")
import logging
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Any, cast

from nonebot_plugin_orm import Model, get_session
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy import func, select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult

logger = logging.getLogger(__name__)


def _conds[T: Model](
    model: type[T],
    filters: dict[str, Any] | None,
) -> list[ColumnElement[bool]]:
    """
    构造SQLAlchemy的条件表达式列表（同步工具函数，无I/O）。
    参数：
        model: ORM模型类
        filters: 字段名到值的映射，支持None、单值、序列
    返回：
        SQLAlchemy条件表达式列表
    """
    if not filters:
        return []
    c: list[ColumnElement[bool]] = []
    for k, v in filters.items():
        col = getattr(model, k, None)
        if col is None:
            continue
        if v is None:
            c.append(col.is_(None))
        elif isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
            if len(v) == 0:
                logger.warning(
                    "过滤条件 '%s' 使用了空序列，将生成 `col.in_([])`，"
                    "可能永不匹配任何记录",
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
    """
    构造SQLAlchemy的排序表达式列表（同步工具函数，无I/O）。
    参数：
        model: ORM模型类
        order_by: 排序字段名序列，支持"-字段"降序
    返回：
        SQLAlchemy排序表达式列表
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
                    "排序字段 '%s' 在模型 '%s' 中不存在，已忽略",
                    key[1:],
                    model.__name__,
                )
        else:
            col = getattr(model, key, None)
            if col is not None:
                o.append(col.asc())
            else:
                logger.warning(
                    "排序字段 '%s' 在模型 '%s' 中不存在，已忽略", key, model.__name__
                )
    return o


def _get_column_names[T: Model](model: type[T]) -> set[str] | None:
    """
    获取模型的所有数据库列名（同步工具函数，使用 inspect，但只读取映射元数据，无I/O）。
    返回：
        - set[str]：列名集合；
        - None：无法获取时返回 None，此时不进行字段过滤。
    """
    try:
        mapper = inspect(model)
        return {c.key for c in mapper.columns}
    except Exception:  # noqa: BLE001
        logger.warning("无法检查模型 %s 的列信息，将不进行更新字段过滤", model.__name__)
        return None


# ----------------- 单条操作（全部异步 / 非阻塞）-----------------


async def create[T: Model](model: type[T], **fields: Any) -> tuple[T | None, bool]:
    """
    异步创建一条新记录。
    参数：
        model: ORM模型类
        **fields: 字段名及其值
    返回：
        (新创建的模型对象, 状态)
        状态为 True 表示成功，False 表示失败。
    """
    async with get_session() as s:
        obj = model(**fields)
        s.add(obj)
        try:
            await s.commit()
            await s.refresh(obj)
        except SQLAlchemyError:
            logger.exception("创建记录失败")
            await s.rollback()
            return None, False
        else:
            return obj, True


async def get_one[T: Model](
    model: type[T], filters: dict[str, Any]
) -> tuple[T | None, bool]:
    """
    异步获取符合条件的单条记录。
    注意：当发生数据库异常时，返回 (None, False)，调用方无法仅凭返回值区分
    “无记录”与“查询出错”，如需区分请检查日志。
    参数：
        model: ORM模型类
        filters: 字段名到值的映射
    返回：
        (模型对象或 None, 状态)
        状态为 True 表示查到结果，False 表示无结果或发生异常。
    """
    async with get_session() as s:
        try:
            stmt = select(model)
            cs = _conds(model, filters)
            if cs:
                stmt = stmt.where(*cs)
            stmt = stmt.limit(1)
            res = await s.execute(stmt)
            obj = res.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("查询单条记录失败")
            return None, False
        else:
            return obj, obj is not None


async def _create_obj[T: Model](
    s: Any,
    model: type[T],
    filters: dict[str, Any],
    defaults: dict[str, Any] | None,
    stmt: Any,
) -> tuple[T | None, bool, bool]:
    """辅助函数：创建记录，若出现完整性冲突则重试查询已存在记录。"""
    data = dict(filters)
    if defaults:
        data.update(defaults)
    obj = model(**data)
    s.add(obj)
    try:
        await s.commit()
        await s.refresh(obj)
    except IntegrityError:
        await s.rollback()
        try:
            res2 = await s.execute(stmt)
            obj2 = res2.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("重试查询失败")
            return None, False, False
        if obj2 is None:
            logger.exception("唯一约束冲突后未找到记录，数据可能不一致")
            return None, False, False
        return obj2, False, True
    except SQLAlchemyError:
        logger.exception("创建记录失败")
        await s.rollback()
        return None, False, False
    else:
        return obj, True, True


async def get_or_create[T: Model](
    model: type[T],
    defaults: dict[str, Any] | None = None,
    **filters: Any,
) -> tuple[T | None, bool, bool]:
    """
    异步获取或创建一条记录。
    若存在则返回，不存在则新建。
    参数：
        model: ORM模型类
        defaults: 默认字段值
        **filters: 查找条件
    返回：
        (对象, 是否新建, 状态)
        状态为 True 表示操作成功，False 表示异常。
    """
    async with get_session() as s:
        cs = _conds(model, filters)
        stmt = select(model)
        if cs:
            stmt = stmt.where(*cs)
        stmt = stmt.limit(1)
        try:
            res = await s.execute(stmt)
            obj = res.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("查询记录失败")
            return None, False, False

        if obj is not None:
            return obj, False, True

        return await _create_obj(s, model, filters, defaults, stmt)


async def _update_existing[T: Model](
    s: Any,
    model: type[T],
    cs: list[ColumnElement[bool]],
    defaults: dict[str, Any] | None,
    obj: T,
) -> tuple[T, bool, bool]:
    """辅助函数：更新已存在记录的值。"""
    update_values = defaults or {}
    if not update_values:
        return obj, False, True
    stmt_update = sqlalchemy_update(model)
    if cs:
        stmt_update = stmt_update.where(*cs)
    stmt_update = stmt_update.values(**update_values)
    try:
        await s.execute(stmt_update)
        await s.commit()
        await s.refresh(obj)
    except SQLAlchemyError:
        logger.exception("更新记录失败")
        await s.rollback()
        return obj, False, False
    else:
        return obj, False, True


async def _create_new[T: Model](
    s: Any,
    model: type[T],
    filters: dict[str, Any],
    defaults: dict[str, Any] | None,
    stmt: Any,
) -> tuple[T | None, bool, bool]:
    """辅助函数：创建新记录，处理可能的完整性冲突并重试。"""
    data = dict(filters)
    if defaults:
        data.update(defaults)
    obj = model(**data)
    s.add(obj)
    try:
        await s.commit()
        await s.refresh(obj)
    except IntegrityError:
        await s.rollback()
        try:
            res2 = await s.execute(stmt)
            obj2 = res2.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("重试查询失败")
            return None, False, False
        if obj2 is None:
            logger.exception("唯一约束冲突后未找到记录，数据可能不一致")
            return None, False, False
        return obj2, False, True
    except SQLAlchemyError:
        logger.exception("创建记录失败")
        await s.rollback()
        return None, False, False
    else:
        return obj, True, True


async def update_or_create[T: Model](
    model: type[T],
    filters: dict[str, Any],
    defaults: dict[str, Any] | None = None,
) -> tuple[T | None, bool, bool]:
    """
    异步更新或创建一条记录。
    若存在则更新，不存在则创建。
    注意：本操作不是原子 upsert，更新分支采用“先查后更新”方式，并发写入时
    可能出现更新丢失。若需要原子性（如计数器），请使用数据库原生的
    INSERT ... ON CONFLICT ... DO UPDATE 等机制。
    参数：
        model: ORM模型类
        filters: 查找条件
        defaults: 默认字段值
    返回：
        (对象, 是否新建, 状态)
        状态为 True 表示操作成功，False 表示异常。
    """
    async with get_session() as s:
        cs = _conds(model, filters)
        stmt = select(model)
        if cs:
            stmt = stmt.where(*cs)
        stmt = stmt.limit(1)
        try:
            res = await s.execute(stmt)
            obj = res.scalar_one_or_none()
        except SQLAlchemyError:
            logger.exception("查询记录失败")
            return None, False, False

        if obj is not None:
            return await _update_existing(s, model, cs, defaults, obj)
        return await _create_new(s, model, filters, defaults, stmt)


async def update[T: Model](
    model: type[T],
    filters: dict[str, Any],
    values: dict[str, Any],
) -> tuple[int, bool]:
    """
    异步更新符合条件的记录。
    参数：
        model: ORM模型类
        filters: 筛选条件
        values: 要更新的字段及其值（需为数据库列名）
    返回：
        (受影响的行数, 状态)
        - 行数为 -1 表示影响行数未知。
        - 状态为 True 表示成功，False 表示失败。
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
                        "字段 '%s' 不是模型 '%s' 的有效数据库列，已忽略",
                        k,
                        model.__name__,
                    )
        else:
            # 无法获取列信息时，不过滤，由数据库自行校验
            logger.info(
                "无法获取模型 '%s' 的列信息，未过滤字段，"
                "若传入非数据库列可能导致更新失败",
                model.__name__,
            )
            update_values = values

        if not update_values:
            return 0, True

        stmt = sqlalchemy_update(model)
        cs = _conds(model, filters)
        if cs:
            stmt = stmt.where(*cs)
        stmt = stmt.values(**update_values)

        try:
            result = cast("CursorResult[Any]", await s.execute(stmt))
            await s.commit()
        except SQLAlchemyError:
            logger.exception("更新记录失败")
            await s.rollback()
            return 0, False
        else:
            rowcount = result.rowcount
            return (int(rowcount) if rowcount is not None else -1), True


async def delete[T: Model](model: type[T], filters: dict[str, Any]) -> tuple[int, bool]:
    """
    异步删除符合条件的记录。
    参数：
        model: ORM模型类
        filters: 筛选条件
    返回：
        (删除的行数, 状态)
        - 行数为 -1 表示影响行数未知。
        - 状态为 True 表示成功，False 表示失败。
    """
    async with get_session() as s:
        stmt = sqlalchemy_delete(model)
        cs = _conds(model, filters)
        if cs:
            stmt = stmt.where(*cs)

        try:
            result = cast("CursorResult[Any]", await s.execute(stmt))
            await s.commit()
        except SQLAlchemyError:
            logger.exception("删除记录失败")
            await s.rollback()
            return 0, False
        else:
            rowcount = result.rowcount
            return (int(rowcount) if rowcount is not None else -1), True


async def exists[T: Model](
    model: type[T], filters: dict[str, Any]
) -> tuple[bool, bool]:
    """
    异步判断是否存在符合条件的记录。
    参数：
        model: ORM模型类
        filters: 筛选条件
    返回：
        (是否存在, 状态)
        状态为 True 表示查询成功，False 表示异常。
    """
    async with get_session() as s:
        try:
            stmt = select(1).select_from(model)
            cs = _conds(model, filters)
            if cs:
                stmt = stmt.where(*cs)
            stmt = stmt.limit(1)
            res = await s.execute(stmt)
            found = res.scalar_one_or_none() is not None
        except SQLAlchemyError:
            logger.exception("存在性查询失败")
            return False, False
        else:
            return found, True


# ----------------- 批量操作（全部异步 / 非阻塞）-----------------


async def bulk_create[T: Model](
    model: type[T], objs: list[dict[str, Any]], *, commit: bool = True
) -> tuple[list[T], bool]:
    """
    异步批量创建多条记录。
    注意：若需要极高并发插入，可考虑在外部使用 asyncio.gather 并发调用
    本函数或单个 create，但应注意数据库连接池上限。
    参数：
        model: ORM模型类
        objs: 字段字典列表
        commit: 是否立即提交事务。若为 False，返回的实例可能未持久化且无主键，
                调用方需要自行 commit() 并 refresh() 以获取数据库生成的值。
    返回：
        (新创建的模型对象列表, 状态)
        状态为 True 表示成功，False 表示失败。
    """
    async with get_session() as s:
        instances = [model(**fields) for fields in objs]
        s.add_all(instances)
        if commit:
            try:
                await s.commit()
                for obj in instances:
                    await s.refresh(obj)
            except SQLAlchemyError:
                logger.exception("批量创建记录失败")
                await s.rollback()
                return [], False
            else:
                return instances, True
        logger.debug("批量创建：commit=False，返回的实例尚未刷新，可能缺少自增主键等值")
        return instances, True


async def list_items[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    order_by: Sequence[str] | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[T], bool]:
    """
    异步获取符合条件的多条记录列表（一次性加载至内存）。
    参数：
        model: ORM模型类
        filters: 字段名到值的映射
        order_by: 排序字段
        offset: 偏移量
        limit: 限制条数
    返回：
        (模型对象列表, 状态)
        状态为 True 表示成功，False 表示失败。
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
            items = list(res.scalars().all())
        except SQLAlchemyError:
            logger.exception("查询列表失败")
            return [], False
        else:
            return items, True


async def async_iterate[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    order_by: Sequence[str] | None = None,
    batch_size: int = 1000,
) -> AsyncGenerator[T]:
    """
    异步迭代大型结果集，避免一次性加载所有记录导致内存压力。
    每次从数据库异步获取一批记录，使用 yield 逐条产出。
    参数：
        model: ORM模型类
        filters: 过滤条件
        order_by: 排序字段
        batch_size: 每批次从数据库获取的行数（默认 1000）
    产出：
        每次 yield 一个模型实例
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
            # 使用流式执行以避免一次性加载全部结果
            result = await s.stream(stmt, execution_options={"yield_per": batch_size})
            async for row in result:
                # stream 返回的是 Row 对象，需提取实体
                yield row[0]
        except SQLAlchemyError:
            logger.exception("异步迭代数据失败")
            return


async def count[T: Model](
    model: type[T], filters: dict[str, Any] | None = None
) -> tuple[int, bool]:
    """
    异步统计符合条件的记录数量。
    参数：
        model: ORM模型类
        filters: 字段名到值的映射
    返回：
        (记录数, 状态)
        状态为 True 表示成功，False 表示失败。
    """
    async with get_session() as s:
        try:
            stmt = select(func.count("*")).select_from(model)
            cs = _conds(model, filters)
            if cs:
                stmt = stmt.where(*cs)
            res = await s.execute(stmt)
            return int(res.scalar_one()), True
        except SQLAlchemyError:
            logger.exception("统计记录数失败")
            return 0, False
