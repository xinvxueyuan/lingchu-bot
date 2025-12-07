"""数据库CRUD函数"""

from collections.abc import Sequence
from typing import Any

from nonebot import require
from nonebot_plugin_orm import Model, get_session
from sqlalchemy import func, select

require("nonebot_plugin_orm")


def _conds[T: Model](model: type[T], filters: dict[str, Any] | None) -> list:
    if not filters:
        return []
    c = []
    for k, v in filters.items():
        col = getattr(model, k, None)
        if col is None:
            continue
        if v is None:
            c.append(col.is_(None))
        elif isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
            c.append(col.in_(list(v)))
        else:
            c.append(col == v)
    return c


def _orders[T: Model](model: type[T], order_by: Sequence[str] | None) -> list:
    if not order_by:
        return []
    o = []
    for key in order_by:
        if key.startswith("-"):
            col = getattr(model, key[1:], None)
            if col is not None:
                o.append(col.desc())
        else:
            col = getattr(model, key, None)
            if col is not None:
                o.append(col.asc())
    return o


async def create[T: Model](model: type[T], **fields: Any) -> T:
    async with get_session() as s:
        obj = model(**fields)
        s.add(obj)
        await s.flush()
        await s.refresh(obj)
        await s.commit()
        return obj


async def get_one[T: Model](model: type[T], filters: dict[str, Any]) -> T | None:
    async with get_session() as s:
        stmt = select(model).where(*_conds(model, filters)).limit(1)
        res = await s.execute(stmt)
        return res.scalar_one_or_none()


async def list_items[T: Model](
    model: type[T],
    filters: dict[str, Any] | None = None,
    order_by: Sequence[str] | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[T]:
    async with get_session() as s:
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


async def count[T: Model](model: type[T], filters: dict[str, Any] | None = None) -> int:
    async with get_session() as s:
        stmt = select(func.count()).select_from(model).where(*_conds(model, filters))
        res = await s.execute(stmt)
        return int(res.scalar_one())


async def update[T: Model](
    model: type[T],
    filters: dict[str, Any],
    values: dict[str, Any],
) -> int:
    async with get_session() as s:
        res = await s.execute(select(model).where(*_conds(model, filters)))
        objs = list(res.scalars().all())
        for obj in objs:
            for k, v in values.items():
                if hasattr(obj, k):
                    setattr(obj, k, v)
        await s.commit()
        return len(objs)


async def delete[T: Model](model: type[T], filters: dict[str, Any]) -> int:
    async with get_session() as s:
        res = await s.execute(select(model).where(*_conds(model, filters)))
        objs = list(res.scalars().all())
        for obj in objs:
            s.delete(obj)
        await s.commit()
        return len(objs)


async def get_or_create[T: Model](
    model: type[T],
    defaults: dict[str, Any] | None = None,
    **filters: Any,
) -> tuple[T, bool]:
    obj = await get_one(model, filters)
    if obj is not None:
        return obj, False
    data = dict(filters)
    if defaults:
        data.update(defaults)
    return await create(model, **data), True


async def exists[T: Model](model: type[T], filters: dict[str, Any]) -> bool:
    return (await get_one(model, filters)) is not None
