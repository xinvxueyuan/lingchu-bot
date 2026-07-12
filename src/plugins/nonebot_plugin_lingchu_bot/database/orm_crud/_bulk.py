"""批量与 upsert 操作：bulk_create、upsert、list_items、async_iterate_safe。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model, get_session
from sqlalchemy import select, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError

from ._base import (
    DatabaseError,
    _combined_conditions,
    _get_column_map,
    _get_session_dialect_name,
    _orders,
    _validate_column_values,
    logger,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.elements import ColumnElement


async def _finalize_bulk_create[T: Model](
    session: AsyncSession,
    instances: Sequence[T],
    *,
    commit: bool,
) -> None:
    if commit:
        await session.commit()
        for obj in instances:
            await session.refresh(obj)
    else:
        await session.flush()


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
                await _finalize_bulk_create(s, instances, commit=commit)
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
            await _finalize_bulk_create(s, created, commit=commit)
        except SQLAlchemyError as e:
            await s.rollback()
            raise DatabaseError("Bulk create failed") from e
        return created, failed


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
    """按数据库方言创建 upsert insert 语句。

    支持 2 个方言：SQLite / PostgreSQL。MySQL / MariaDB 不使用本函数
    （由 ``_mysql_upsert`` 直接处理）。Oracle / SQL Server 不使用本函数
    （由 ``_oracle_upsert`` / ``_mssql_upsert`` 用 ``MERGE INTO`` 原始 SQL）。
    """
    if dialect_name == "sqlite":
        if constraint is not None:
            raise ValueError("SQLite upsert requires conflict_fields")
        return sqlite_insert(model)
    if dialect_name == "postgresql":
        return postgresql_insert(model)
    raise DatabaseError(
        f"Upsert via dialect-insert is not supported for '{dialect_name}'; "
        "use the dialect-specific helper"
    )


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


_MISSING_DEFAULT = object()


def _evaluate_python_column_default(default: Any) -> Any:
    """Return a Python-side SQLAlchemy column default, if it can be evaluated."""
    if default is None:
        return _MISSING_DEFAULT
    if getattr(default, "is_scalar", False):
        return default.arg
    if getattr(default, "is_callable", False):
        try:
            return default.arg(None)
        except TypeError:
            return default.arg()
    return _MISSING_DEFAULT


def _prepare_merge_insert_values[T: Model](
    model: type[T],
    insert_values: dict[str, Any],
) -> dict[str, Any]:
    """Fill raw MERGE insert values with Python-side defaults.

    SQLAlchemy applies ``Column.default`` when it builds INSERT constructs. The
    Oracle and SQL Server upsert path uses raw text MERGE, so those defaults must
    be evaluated before rendering the INSERT branch.
    """
    prepared = dict(insert_values)
    table = getattr(model, "__table__", None)
    if table is None:
        return prepared

    for column in table.columns:
        key = column.key
        if key in prepared:
            continue
        if column.primary_key and column.identity is not None:
            continue

        default_value = _evaluate_python_column_default(column.default)
        if default_value is not _MISSING_DEFAULT:
            prepared[key] = default_value

    return prepared


def _merge_target_identifiers[T: Model](
    s: AsyncSession,
    model: type[T],
    keys: Sequence[str],
) -> tuple[str, dict[str, str]]:
    """Return dialect-formatted target table and column identifiers for MERGE."""
    dialect = s.get_bind().dialect
    preparer = dialect.identifier_preparer
    table = getattr(model, "__table__", None)
    if table is None:
        return model.__tablename__, {key: key for key in keys}

    target_table = preparer.format_table(table)
    target_columns = {
        key: preparer.format_column(table.columns[key])
        for key in keys
        if key in table.columns
    }
    return target_table, target_columns


def _build_merge_sql(
    target_clause: str,
    target_columns: dict[str, str],
    insert_values: dict[str, Any],
    conflict_keys: list[str],
    update_keys: list[str],
    explicit_update_values: dict[str, Any] | None,
    *,
    use_dual: bool,
) -> tuple[str, dict[str, Any]]:
    """构造 Oracle / SQL Server 的 ``MERGE INTO`` SQL 与绑定参数。

    SQLAlchemy 2.0.51 不提供 ``sqlalchemy.dialects.{oracle,mssql}.insert``，
    故 Oracle / SQL Server 的 upsert 走显式 ``MERGE INTO``。

    Args:
        target_clause: 方言格式化后的目标表名与别名 / 锁提示子句。
        target_columns: 方言格式化后的目标列名。
        insert_values: 完整插入字段；也作为基础绑定参数。
        conflict_keys: ``ON`` 子句的关联列。
        update_keys: 隐式模式下要更新的列（不在显式覆盖时使用）。
        explicit_update_values: 显式更新字典（覆盖 insert_values 绑定）。
        use_dual: True 为 Oracle（``SELECT ... FROM DUAL``），
            False 为 SQL Server（裸 ``SELECT :p1 AS c1, ...``）。

    Returns:
        ``(sql, params)``，其中 ``sql`` 为参数化 MERGE 文本，``params`` 为
        要传给 ``session.execute`` 的绑定字典。

    Raises:
        无 / None.
    """
    insert_param_names = {
        key: f"p{idx}" for idx, key in enumerate(insert_values, start=1)
    }
    source_column_names = {
        key: f"c{idx}" for idx, key in enumerate(insert_values, start=1)
    }
    update_param_names = (
        {key: f"u{idx}" for idx, key in enumerate(explicit_update_values, start=1)}
        if explicit_update_values is not None
        else {}
    )

    insert_cols = ", ".join(target_columns[key] for key in insert_values)
    src_select = ", ".join(
        f":{insert_param_names[key]} AS {source_column_names[key]}"
        for key in insert_values
    )
    on_predicates = " AND ".join(
        f"t.{target_columns[key]} = s.{source_column_names[key]}"
        for key in conflict_keys
    )

    if explicit_update_values is not None:
        set_parts = [
            f"t.{target_columns[key]} = :{update_param_names[key]}"
            for key in explicit_update_values
        ]
    else:
        set_parts = [
            f"t.{target_columns[key]} = s.{source_column_names[key]}"
            for key in update_keys
        ]
    set_clause = ", ".join(set_parts)
    insert_values_clause = ", ".join(
        f"s.{source_column_names[key]}" for key in insert_values
    )

    source = (
        f"(SELECT {src_select} FROM DUAL) s" if use_dual else f"(SELECT {src_select}) s"
    )

    merge_sql = (
        f"MERGE INTO {target_clause} "
        f"USING {source} "
        f"ON ({on_predicates}) "
        f"WHEN MATCHED THEN UPDATE SET {set_clause} "
        f"WHEN NOT MATCHED THEN INSERT ({insert_cols}) "
        f"VALUES ({insert_values_clause});"
    )

    params: dict[str, Any] = {
        insert_param_names[key]: value for key, value in insert_values.items()
    }
    if explicit_update_values is not None:
        params.update(
            {
                update_param_names[key]: value
                for key, value in explicit_update_values.items()
            }
        )
    return merge_sql, params


async def upsert[T: Model](
    model: type[T],
    insert_values: dict[str, Any],
    *,
    conflict_fields: Sequence[str] | None = None,
    constraint: str | None = None,
    update_values: dict[str, Any] | None = None,
) -> T:
    """执行方言级原子 upsert（SQLite/PostgreSQL/MySQL/MariaDB/Oracle/SQL Server）。

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

        if dialect_name in {"mysql", "mariadb"}:
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

        if dialect_name == "oracle":
            return await _oracle_upsert(
                s,
                model,
                insert_values,
                columns,
                conflict_keys,
                update_keys,
                explicit_update_values,
                constraint,
            )

        if dialect_name == "mssql":
            return await _mssql_upsert(
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


async def _mysql_upsert[T: Model](
    s: AsyncSession,
    model: type[T],
    insert_values: dict[str, Any],
    columns: dict[str, Any],
    conflict_keys: list[str],
    update_keys: list[str],
    explicit_update_values: dict[str, Any] | None,
    constraint: str | None,
) -> T:
    """MySQL / MariaDB 方言的 upsert 实现。

    使用 ``INSERT ... ON DUPLICATE KEY UPDATE`` 语义。MySQL / MariaDB 不支持
    ``RETURNING``，因此执行后通过 ``conflict_fields`` 做一次 follow-up
    ``SELECT`` 取回最新行。

    MariaDB 10.3+ 支持 ON DUPLICATE KEY UPDATE，与 MySQL 协议兼容；MariaDB
    官方驱动下 SQLAlchemy 仍以 ``mysql`` dialect 路径编译（``mysql_insert``
    同时适用于两个方言）。``_get_session_dialect_name`` 返回 ``"mariadb"``
    时，本函数被复用。
    """
    if constraint is not None:
        raise ValueError(
            "MySQL/MariaDB upsert does not support constraint; use conflict_fields"
        )
    if not conflict_keys:
        raise ValueError(
            "MySQL/MariaDB upsert requires conflict_fields for follow-up SELECT"
        )

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


def _is_oracle_unique_constraint_violation(error: SQLAlchemyError) -> bool:
    """Return whether an Oracle DBAPI error reports ORA-00001."""
    visited: set[int] = set()
    stack: list[BaseException | None] = [error]
    while stack:
        current = stack.pop()
        if current is None or id(current) in visited:
            continue
        visited.add(id(current))
        if "ORA-00001" in str(current):
            return True
        stack.extend(
            [
                getattr(current, "orig", None),
                current.__cause__,
                current.__context__,
            ]
        )
    return False


async def _oracle_upsert[T: Model](
    s: AsyncSession,
    model: type[T],
    insert_values: dict[str, Any],
    columns: dict[str, Any],
    conflict_keys: list[str],
    update_keys: list[str],
    explicit_update_values: dict[str, Any] | None,
    constraint: str | None,
) -> T:
    """Oracle upsert 实现（手写 ``MERGE INTO``）。

    SQLAlchemy 2.0.51 不提供 ``sqlalchemy.dialects.oracle.insert`` 与方言级
    ``on_conflict_do_update``，因此使用显式 ``MERGE INTO ... USING (SELECT
    ... FROM DUAL) s ...`` 语句 + 命名参数绑定。Oracle 不支持 ``RETURNING``，
    执行后通过 ``conflict_fields`` 做一次 follow-up ``SELECT`` 取回最新行。
    """
    if constraint is not None:
        raise ValueError(
            "Oracle upsert does not support constraint; use conflict_fields"
        )
    if not conflict_keys:
        raise ValueError("Oracle upsert requires conflict_fields for MERGE ON clause")

    insert_values = _prepare_merge_insert_values(model, insert_values)
    target_keys = list(insert_values)
    if explicit_update_values is not None:
        target_keys.extend(
            key for key in explicit_update_values if key not in insert_values
        )
    target_table, target_columns = _merge_target_identifiers(s, model, target_keys)
    merge_sql, params = _build_merge_sql(
        f"{target_table} t",
        target_columns,
        insert_values,
        conflict_keys,
        update_keys,
        explicit_update_values,
        use_dual=True,
    )
    stmt = text(merge_sql)
    unique_conflict_error: SQLAlchemyError | None = None

    try:
        await s.execute(stmt, params)
        await s.commit()
    except SQLAlchemyError as e:
        await s.rollback()
        if not _is_oracle_unique_constraint_violation(e):
            raise DatabaseError("Upsert failed") from e
        unique_conflict_error = e

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
        if unique_conflict_error is not None:
            raise DatabaseError("Upsert failed") from unique_conflict_error
        raise DatabaseError("Upsert failed to fetch row") from e
    if obj is None:
        if unique_conflict_error is not None:
            raise DatabaseError("Upsert failed") from unique_conflict_error
        raise DatabaseError("Upsert succeeded but row not found")
    return obj


async def _mssql_upsert[T: Model](
    s: AsyncSession,
    model: type[T],
    insert_values: dict[str, Any],
    columns: dict[str, Any],
    conflict_keys: list[str],
    update_keys: list[str],
    explicit_update_values: dict[str, Any] | None,
    constraint: str | None,
) -> T:
    """SQL Server upsert 实现（手写 ``MERGE INTO``）。

    SQLAlchemy 2.0.51 不提供 ``sqlalchemy.dialects.mssql.insert`` 与方言级
    ``on_conflict_do_update``，因此使用显式 ``MERGE INTO ... USING (SELECT
    ...) s ...`` 语句 + 命名参数绑定。SQL Server 不支持 ``RETURNING``，执行
    后通过 ``conflict_fields`` 做一次 follow-up ``SELECT`` 取回最新行。
    """
    if constraint is not None:
        raise ValueError(
            "SQL Server upsert does not support constraint; use conflict_fields"
        )
    if not conflict_keys:
        raise ValueError(
            "SQL Server upsert requires conflict_fields for MERGE ON clause"
        )

    insert_values = _prepare_merge_insert_values(model, insert_values)
    target_keys = list(insert_values)
    if explicit_update_values is not None:
        target_keys.extend(
            key for key in explicit_update_values if key not in insert_values
        )
    target_table, target_columns = _merge_target_identifiers(s, model, target_keys)
    merge_sql, params = _build_merge_sql(
        f"{target_table} WITH (HOLDLOCK) AS t",
        target_columns,
        insert_values,
        conflict_keys,
        update_keys,
        explicit_update_values,
        use_dual=False,
    )
    stmt = text(merge_sql)

    try:
        # Set a 5-second lock timeout so MERGE fails fast instead of
        # hanging forever when HOLDLOCK range locks conflict.
        await s.execute(text("SET LOCK_TIMEOUT 5000"))
        await s.execute(stmt, params)
        await s.commit()
    except SQLAlchemyError as e:
        await s.rollback()
        raise DatabaseError("Upsert failed") from e

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


async def list_items[T: Model](
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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.
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


async def async_iterate_safe[T: Model](
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
        conditions: 额外的 SQLAlchemy 列条件 / Extra SQLAlchemy column conditions.
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
