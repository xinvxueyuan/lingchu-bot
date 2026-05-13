"""Unit tests for database CRUD tools in db_client.py.

This module provides comprehensive unit tests for all database operations including:
create, get_one, get_or_create, update_or_create, update, delete, exists, bulk_create,
list_items, async_iterate_safe, count, and internal utility functions. All tests use
mock objects to simulate asynchronous database sessions, ensuring no dependency on
real databases.

The test suite validates error handling, edge cases, transaction management, and
proper SQLAlchemy integration. Each test class focuses on a specific function or
utility, with fixtures providing reusable mock objects and session configurations.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot_plugin_orm import Model
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import (
    ROWCOUNT_UNKNOWN,
    DatabaseError,
    _conds,
    _get_column_names,
    _is_fk_constraint_violation,
    _orders,
    async_iterate_safe,
    bulk_create,
    count,
    create,
    delete,
    exists,
    get_one,
    get_or_create,
    list_items,
    update,
    update_or_create,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Generator
    from unittest.mock import Mock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_LIMIT = 100
BATCH_SIZE = 1000

# Test constants
ID_1 = 1
ID_2 = 2
ID_3 = 3
ID_4 = 4
ID_5 = 5
ID_10 = 10
ID_20 = 20
ID_999 = 999
COUNT_EXPECTED = 42
ROWCOUNT_SUCCESS = 3
ROWCOUNT_DELETE = 2
COLLS_LEN_1 = 1
COLLS_LEN_2 = 2
REFRESH_COUNT_2 = 2
COMMIT_COUNT_2 = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class FakeModel(Model):
    """Mock model for testing database operations.

    A test model with MagicMock column attributes (id, name, age) that allows
    internal functions like _conds and _orders to work correctly during testing.

    Attributes:
        id (Any): Mock column for record identifiers.
        name (Any): Mock column for record names.
        age (Any): Mock column for record ages.
    """

    __abstract__ = True

    id: Any = MagicMock()
    name: Any = MagicMock()
    age: Any = MagicMock()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize FakeModel with arbitrary keyword arguments.

        Allows dynamic attribute assignment for flexible test data creation.

        Args:
            **kwargs (Any): Arbitrary keyword arguments to set as model attributes.
        """
        super().__init__()
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_sql_constructors() -> Generator[None]:
    """Patch SQLAlchemy constructors in db_client to return MagicMock objects.

    This fixture automatically patches select, sqlalchemy_delete, and
    sqlalchemy_update functions used in db_client module. Ensures consistent
    mock behavior across all tests without manual patching.

    Yields:
        None: Yields during test execution, restores patches afterward.
    """
    with (
        patch(
            "src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud.select",
            MagicMock(return_value=MagicMock()),
        ),
        patch(
            "src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud.sqlalchemy_delete",
            MagicMock(return_value=MagicMock()),
        ),
        patch(
            "src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud.sqlalchemy_update",
            MagicMock(return_value=MagicMock()),
        ),
    ):
        yield


@pytest.fixture
def mock_model() -> type[FakeModel]:
    """Provide a mock model class for testing.

    Returns a FakeModel class with id, name, and age mock attributes that
    simulates a database model for testing CRUD operations.

    Returns:
        type[FakeModel]: The FakeModel class ready for instantiation in tests.
    """
    return FakeModel


@pytest.fixture
def mock_async_session() -> Mock:
    """Provide a mock AsyncSession for database operations.

    Creates an AsyncMock object that simulates SQLAlchemy's AsyncSession behavior,
    including nested transaction support via savepoints.

    Returns:
        Mock: An AsyncMock configured with typical database session methods.
    """
    sess = AsyncMock()
    savepoint = AsyncMock()
    sess.begin_nested.return_value = savepoint
    return sess


@pytest.fixture(autouse=True)
def _patch_get_session(mock_async_session: Mock) -> Generator[None]:
    """Automatically patch get_session to use the mock session in all tests.

    Replaces the real get_session function with one that returns a mock session,
    ensuring all database operations in tests use the same controlled mock object.

    Args:
        mock_async_session (Mock): The mock AsyncSession fixture to inject.

    Yields:
        None: Yields during test execution, restores get_session afterward.
    """
    with patch(
        "src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud.get_session",
        new=lambda: _fake_session_ctx(mock_async_session),
    ):
        yield


@asynccontextmanager
async def _fake_session_ctx(mock_session: Mock) -> AsyncIterator[Mock]:
    """Simulate an async context manager for database sessions.

    Provides the async context protocol expected by the database client, yielding
    the mock session for use within the context.

    Args:
        mock_session (Mock): The mock AsyncSession to yield.

    Yields:
        Mock: The mock session object for use in async with blocks.
    """
    yield mock_session


@pytest.fixture
def exec_result_mock() -> Mock:
    """Provide a generic mock for database query execution results.

    Returns a MagicMock pre-configured with common result methods (scalar_one_or_none,
    scalars, scalar_one) and rowcount attribute.

    Returns:
        Mock: A MagicMock configured as a typical SQLAlchemy CursorResult.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    result.scalar_one.return_value = 0
    result.rowcount = 1
    return result


# ---------------------------------------------------------------------------
# 内部工具函数测试
# ---------------------------------------------------------------------------


class TestIsFkConstraintViolation:
    """Test suite for _is_fk_constraint_violation function.

    Validates detection of foreign key constraint violations in SQLAlchemy
    IntegrityErrors through SQLSTATE codes and error message patterns.
    """

    def test_sqlstate_23503(self) -> None:
        """Test detection of foreign key violation via SQLSTATE 23503.

        Verifies that errors with SQLSTATE code 23503 are correctly identified
        as foreign key constraint violations.

        Raises:
            AssertionError: If _is_fk_constraint_violation returns False for valid
                FK error.
        """

        class _OrigError(Exception):
            def __init__(self, sqlstate: str) -> None:
                super().__init__()
                self.sqlstate = sqlstate

        e = IntegrityError(statement="", params=(), orig=_OrigError("23503"))
        assert _is_fk_constraint_violation(e) is True

    def test_message_foreign_key(self) -> None:
        """Test detection of foreign key violation via error message.

        Verifies that errors containing 'foreign key' in message are recognized
        as foreign key constraint violations.

        Raises:
            AssertionError: If _is_fk_constraint_violation returns False.
        """
        e = IntegrityError(statement="", params=(), orig=Exception("foreign key"))
        assert _is_fk_constraint_violation(e) is True

    def test_not_violation(self) -> None:
        """Test non-foreign-key constraint violations are not detected.

        Verifies that constraint violations with 'unique' error messages are
        correctly identified as non-foreign-key violations.

        Raises:
            AssertionError: If _is_fk_constraint_violation returns True for non-FK
                error.
        """
        e = IntegrityError(statement="", params=(), orig=Exception("unique"))
        assert _is_fk_constraint_violation(e) is False


class TestConds:
    """Test suite for _conds utility function.

    Validates filter condition conversion from dictionary format to SQLAlchemy
    condition objects, including edge cases and invalid inputs.
    """

    def test_empty_filters(self, mock_model: type[FakeModel]) -> None:
        """Test handling of empty or None filter dictionaries.

        Verifies that None and empty dict inputs result in empty condition lists.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If empty conditions are not returned for empty input.
        """
        assert _conds(mock_model, None) == []
        assert _conds(mock_model, {}) == []

    def test_basic_equals(self, mock_model: type[FakeModel]) -> None:
        """Test basic equality condition generation.

        Verifies that simple key-value filters generate a single condition.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If condition count does not match expected.
        """
        conds = _conds(mock_model, {"name": "test"})
        assert len(conds) == COLLS_LEN_1

    def test_none_filter(self, mock_model: type[FakeModel]) -> None:
        """Test filtering for None values (IS NULL conditions).

        Verifies that None filter values generate proper NULL comparison conditions.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If condition is not generated for None value.
        """
        conds = _conds(mock_model, {"name": None})
        assert len(conds) == COLLS_LEN_1

    def test_sequence_filter(self, mock_model: type[FakeModel]) -> None:
        """Test sequence filtering (IN conditions).

        Verifies that list/sequence values generate IN clause conditions.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If condition is not generated for sequence.
        """
        conds = _conds(mock_model, {"name": ["a", "b"]})
        assert len(conds) == COLLS_LEN_1

    def test_empty_sequence_warning(
        self, mock_model: type[FakeModel], caplog: Any
    ) -> None:
        """Test warning on empty sequence in filters.

        Verifies that empty sequences trigger a warning log message.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            caplog (Any): Pytest logging capture fixture.

        Raises:
            AssertionError: If warning is not logged for empty sequence.
        """
        with caplog.at_level(logging.WARNING):
            _conds(mock_model, {"name": []})
        assert "empty sequence" in caplog.text

    def test_unknown_column_warning(
        self, mock_model: type[FakeModel], caplog: Any
    ) -> None:
        """Test warning on non-existent column in filters.

        Verifies that filters on unknown model columns trigger a warning
        and return empty conditions.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            caplog (Any): Pytest logging capture fixture.

        Raises:
            AssertionError: If warning is not logged or empty list not returned.
        """
        with caplog.at_level(logging.WARNING):
            conds: list = _conds(model=mock_model, filters={"no_such_column": 1})
        assert "not found" in caplog.text
        assert conds == []


class TestOrders:
    """Test suite for _orders utility function.

    Validates conversion of order specifications (list of field names with
    optional direction prefix) to SQLAlchemy ordering clauses.
    """

    def test_empty_orders(self, mock_model: type[FakeModel]) -> None:
        """Test handling of empty or None order specifications.

        Verifies that None and empty list inputs result in empty order lists.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If empty orders are not returned for empty input.
        """
        assert _orders(model=mock_model, order_by=None) == []
        assert _orders(model=mock_model, order_by=[]) == []

    def test_asc_desc(self, mock_model: type[FakeModel]) -> None:
        """Test ascending and descending order specifications.

        Verifies that field names without prefix (ascending) and with '-' prefix
        (descending) generate correct number of order clauses.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If order count does not match expected.
        """
        orders: list = _orders(model=mock_model, order_by=["name", "-age"])
        assert len(orders) == COLLS_LEN_2

    def test_unknown_field(self, mock_model: type[FakeModel], caplog: Any) -> None:
        """Test warning on non-existent field in order specification.

        Verifies that ordering by unknown model fields triggers a warning
        and returns empty orders.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            caplog (Any): Pytest logging capture fixture.

        Raises:
            AssertionError: If warning is not logged or empty list not returned.
        """
        with caplog.at_level(logging.WARNING):
            orders = _orders(mock_model, ["-ghost"])
        assert "not found" in caplog.text
        assert orders == []


class TestGetColumnNames:
    """Test suite for _get_column_names utility function.

    Validates extraction of column names from SQLAlchemy model mappers,
    including error handling for inspection failures.
    """

    def test_success(self, mock_model: type[FakeModel]) -> None:
        """Test successful column name extraction.

        Verifies that _get_column_names correctly extracts column names from
        a mocked inspect result.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If extracted column names don't match expected set.
        """
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud.inspect"
        ) as mock_inspect:
            mapper = MagicMock()
            mapper.columns = [MagicMock(key="id"), MagicMock(key="name")]
            mock_inspect.return_value = mapper
            cols: set[str] | None = _get_column_names(model=mock_model)
            assert cols == {"id", "name"}

    def test_inspect_failure(self, mock_model: type[FakeModel]) -> None:
        """Test handling of inspect failures.

        Verifies that SQLAlchemy inspection errors are caught and None is
        returned to indicate inspection failure.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            AssertionError: If None is not returned on inspection failure.
        """
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud.inspect",
            side_effect=SQLAlchemyError,
        ):
            assert _get_column_names(model=mock_model) is None


# ---------------------------------------------------------------------------
# CRUD 操作测试
# ---------------------------------------------------------------------------


class TestCreate:
    """Test suite for create database operation.

    Validates record creation including success, error handling, and
    session transaction management.
    """

    @pytest.mark.asyncio
    async def test_create_success(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test successful record creation.

        Verifies that a new record is created, committed, and refreshed with
        all mock session methods called as expected.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If session methods not called or object not created.
        """
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()
        obj = await create(mock_model, name="alice")
        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_awaited_once()
        mock_async_session.refresh.assert_awaited_once()
        assert obj.name == "alice"

    @pytest.mark.asyncio
    async def test_create_failure(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test create operation with database error.

        Verifies that database errors during creation raise DatabaseError
        and trigger rollback.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError is not raised on failure.
        """
        mock_async_session.commit.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="create record"):
            await create(model=mock_model, name="bob")
        mock_async_session.rollback.assert_awaited_once()


class TestGetOne:
    """Test suite for get_one database query operation.

    Validates single record retrieval including found, not found, and error cases.
    """

    @pytest.mark.asyncio
    async def test_found(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test retrieving an existing record.

        Verifies that a matching record is found and returned correctly.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If retrieved object doesn't match expected.
        """
        fake_obj = FakeModel(id=ID_1, name="x")
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = (
            fake_obj
        )
        result: FakeModel | None = await get_one(model=mock_model, filters={"id": ID_1})
        assert result is fake_obj

    @pytest.mark.asyncio
    async def test_not_found(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test retrieving a non-existent record.

        Verifies that None is returned when no matching record exists.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If None is not returned for missing record.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = None
        assert await get_one(model=mock_model, filters={"id": ID_999}) is None

    @pytest.mark.asyncio
    async def test_query_failure(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test query failure handling.

        Verifies that database errors during query raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError is not raised.
        """
        mock_async_session.execute.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="query record"):
            await get_one(model=mock_model, filters={"id": 1})


class TestGetOrCreate:
    """Test suite for get_or_create database operation.

    Validates record retrieval or creation with handling of unique constraint
    violations and other edge cases.
    """

    @pytest.mark.asyncio
    async def test_existing(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test retrieving an existing record.

        Verifies that an existing record is returned with created=False.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If record not found or created flag incorrect.
        """
        existing = FakeModel(id=ID_1)
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = (
            existing
        )
        obj, created = await get_or_create(mock_model, id=ID_1)
        assert obj is existing
        assert created is False

    @pytest.mark.asyncio
    async def test_create_new(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test creating a new record when not found.

        Verifies that a new record is created with defaults applied and
        created=True is returned.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If record not created or created flag incorrect.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()
        obj, created = await get_or_create(
            model=mock_model, id=ID_2, defaults={"name": "new"}
        )
        assert created is True
        assert obj.id == ID_2
        assert obj.name == "new"

    @pytest.mark.asyncio
    async def test_unique_conflict_resolve(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test handling of unique constraint conflicts with eventual success.

        Verifies that when a unique constraint violation occurs, the operation
        rolls back, re-queries to find the inserted record, and returns it.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If conflict not properly resolved.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_async_session.commit.side_effect = IntegrityError(
            "duplicate", params=(), orig=Exception("unique")
        )
        existing = FakeModel(id=ID_3, name="old")
        mock_async_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing)),
        ]
        obj, created = await get_or_create(
            model=mock_model, id=ID_3, defaults={"name": "dup"}
        )
        assert obj is existing
        assert created is False
        assert mock_async_session.rollback.called

    @pytest.mark.asyncio
    async def test_foreign_key_violation(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test handling of foreign key constraint violations.

        Verifies that foreign key violations raise DatabaseError without retry.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised for FK violation.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = None
        fk_err = IntegrityError(statement="", params=(), orig=Exception("foreign key"))
        mock_async_session.commit.side_effect = fk_err
        with pytest.raises(expected_exception=DatabaseError, match="Foreign key"):
            await get_or_create(model=mock_model, id=ID_4)

    @pytest.mark.asyncio
    async def test_retry_after_conflict_no_record(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test retry logic when unique conflict resolution query returns None.

        Verifies that the operation retries record creation after rollback if
        re-query finds no record.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If retry logic not executed correctly.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = None
        err = IntegrityError("duplicate", params=(), orig=Exception("unique"))
        res_none = MagicMock()
        res_none.scalar_one_or_none.return_value = None
        mock_async_session.execute.side_effect = [res_none, res_none]
        mock_async_session.commit.side_effect = [err, None]
        mock_async_session.refresh = AsyncMock()
        _obj, created = await get_or_create(
            model=mock_model, id=ID_5, defaults={"name": "x"}
        )
        assert created is True
        assert mock_async_session.rollback.call_count >= 1


class TestUpdateOrCreate:
    """Test suite for update_or_create database operation.

    Validates record update if exists, or creation if not found, with proper
    error handling.
    """

    @pytest.mark.asyncio
    async def test_update_existing(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test updating an existing record.

        Verifies that an existing record is updated with new values and
        created=False is returned.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If record not updated or created flag incorrect.
        """
        existing = FakeModel(id=ID_10, name="old")
        res_first = MagicMock()
        res_first.scalar_one_or_none.return_value = existing
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.side_effect = [res_first, MagicMock(rowcount=1)]
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()
        obj, created = await update_or_create(
            model=mock_model,
            filters={"id": ID_10},
            defaults={"name": "new"},
        )
        assert obj is existing
        assert created is False
        mock_async_session.commit.assert_awaited()
        mock_async_session.refresh.assert_awaited_with(existing)

    @pytest.mark.asyncio
    async def test_create_when_missing(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test creating a new record when query finds nothing.

        Verifies that a new record with filters as attributes is created
        and created=True is returned.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If record not created or created flag incorrect.
        """
        res_first = MagicMock()
        res_first.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.side_effect = [res_first]
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()
        _obj, created = await update_or_create(
            model=mock_model, filters={"id": ID_20}, defaults={"name": "new"}
        )
        assert created is True
        assert _obj.id == ID_20
        assert _obj.name == "new"

    @pytest.mark.asyncio
    async def test_db_error_during_query(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test error handling when query fails.

        Verifies that database errors during the initial query raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.execute.side_effect = SQLAlchemyError()
        with pytest.raises(
            expected_exception=DatabaseError, match="Query failed in update_or_create"
        ):
            await update_or_create(model=mock_model, filters={"id": 1})


class TestUpdate:
    """Test suite for update database operation.

    Validates batch record updates with row count tracking and error handling.
    """

    @pytest.mark.asyncio
    async def test_update_success(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test successful record update.

        Verifies that records matching filters are updated and rowcount is returned.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If rowcount incorrect or commit not called.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.rowcount = ROWCOUNT_SUCCESS
        rc, known = await update(
            model=mock_model, filters={"active": True}, values={"active": False}
        )
        assert rc == ROWCOUNT_SUCCESS
        assert known is True
        mock_async_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_no_values(
        self,
        mock_model: type[FakeModel],
        mock_async_session: Mock,
    ) -> None:
        """Test update with empty values dictionary.

        Verifies that empty values result in zero updates without execution.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If rowcount not zero or known not True.
        """
        _ = mock_async_session
        rc, known = await update(model=mock_model, filters={"id": 1}, values={})
        assert rc == 0
        assert known is True

    @pytest.mark.asyncio
    async def test_update_unknown_rowcount(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test handling when rowcount is unavailable.

        Verifies that ROWCOUNT_UNKNOWN is returned and known flag is False
        when rowcount attribute is missing.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If ROWCOUNT_UNKNOWN not returned or known not False.
        """
        result_mock = MagicMock()
        del result_mock.rowcount
        mock_async_session.execute.return_value = result_mock
        rc, known = await update(model=mock_model, filters={}, values={"x": 1})
        assert rc == ROWCOUNT_UNKNOWN
        assert known is False

    @pytest.mark.asyncio
    async def test_update_invalid_fields_filtered(
        self,
        mock_model: type[FakeModel],
        mock_async_session: Mock,
        caplog: Any,
    ) -> None:
        """Test filtering of invalid column names in values.

        Verifies that invalid columns are removed with warning and only
        valid columns are used in update.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.
            caplog (Any): Pytest logging capture fixture.

        Raises:
            AssertionError: If invalid column not filtered or warning not logged.
        """
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud._get_column_names",
            return_value={"id", "name"},
        ):
            mock_async_session.execute.return_value = MagicMock(rowcount=1)
            with caplog.at_level(logging.WARNING):
                _rc, known = await update(
                    model=mock_model, filters={}, values={"age": 30, "name": "ok"}
                )
            assert "not a valid DB column" in caplog.text
            assert known is True

    @pytest.mark.asyncio
    async def test_update_db_error(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test error handling during update.

        Verifies that database errors raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.execute.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="update records"):
            await update(model=mock_model, filters={}, values={"name": "x"})


class TestDelete:
    """Test suite for delete database operation.

    Validates batch record deletion with row count tracking and error handling.
    """

    @pytest.mark.asyncio
    async def test_delete_success(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test successful record deletion.

        Verifies that records matching filters are deleted and rowcount returned.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If rowcount incorrect or commit not called.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.rowcount = ROWCOUNT_DELETE
        rc, known = await delete(model=mock_model, filters={"id": 1})
        assert rc == ROWCOUNT_DELETE
        assert known is True

    @pytest.mark.asyncio
    async def test_delete_db_error(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test error handling during deletion.

        Verifies that database errors raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.execute.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="delete records"):
            await delete(model=mock_model, filters={"id": 1})


class TestExists:
    """Test suite for exists database check operation.

    Validates existence checking for records matching filters.
    """

    @pytest.mark.asyncio
    async def test_exists_true(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test detecting when a record exists.

        Verifies that exists returns True when matching record is found.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If exists does not return True for found record.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = ID_1
        assert await exists(model=mock_model, filters={"id": ID_1}) is True

    @pytest.mark.asyncio
    async def test_exists_false(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test detecting when a record does not exist.

        Verifies that exists returns False when no matching record is found.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If exists does not return False for missing record.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one_or_none.return_value = None
        assert await exists(model=mock_model, filters={"id": ID_999}) is False

    @pytest.mark.asyncio
    async def test_exists_db_error(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test error handling during existence check.

        Verifies that database errors raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.execute.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="check existence"):
            await exists(model=mock_model, filters={"id": 1})


class TestBulkCreate:
    """Test suite for bulk_create batch operation.

    Validates batch record creation with partial mode and error handling.
    """

    @pytest.mark.asyncio
    async def test_bulk_create_commit(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test bulk creation with full commit (all-or-nothing).

        Verifies that all records are created and committed together, with
        all records refreshed.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If objects not created or refresh not called.
        """
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()
        objs, fails = await bulk_create(
            model=mock_model,
            objs=[{"name": "a"}, {"name": "b"}],
            commit=True,
            partial=False,
        )
        assert len(objs) == COLLS_LEN_2
        assert fails == []
        assert mock_async_session.commit.called
        assert mock_async_session.refresh.call_count == REFRESH_COUNT_2

    @pytest.mark.asyncio
    async def test_bulk_create_partial(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test bulk creation with partial mode (skip on error).

        Verifies that successful records are created even if some fail,
        and failures are collected.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If partial creation not working correctly.
        """
        savepoint_ok = AsyncMock()
        savepoint_fail = AsyncMock()
        savepoint_fail.commit.side_effect = SQLAlchemyError("fail")
        mock_async_session.begin_nested.side_effect = [savepoint_ok, savepoint_fail]
        mock_async_session.refresh = AsyncMock()
        objs, fails = await bulk_create(
            model=mock_model,
            objs=[{"name": "ok"}, {"name": "bad"}],
            commit=True,
            partial=True,
        )
        assert len(objs) == COLLS_LEN_1
        assert objs[0].name == "ok"
        assert len(fails) == COLLS_LEN_1
        assert fails[0][0] == ID_1

    @pytest.mark.asyncio
    async def test_bulk_create_non_partial_failure(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test bulk creation failure in non-partial mode.

        Verifies that the entire operation is rolled back when any error
        occurs in non-partial mode.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.commit.side_effect = SQLAlchemyError("bulk fail")
        with pytest.raises(
            expected_exception=DatabaseError, match="Bulk create failed"
        ):
            await bulk_create(
                model=mock_model, objs=[{"name": "x"}], commit=True, partial=False
            )
        mock_async_session.rollback.assert_awaited_once()


class TestListItems:
    """Test suite for list_items query operation.

    Validates fetching multiple records with filtering, ordering, and pagination.
    """

    @pytest.mark.asyncio
    async def test_basic_list(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test basic list retrieval without filters.

        Verifies that all records can be fetched without any conditions.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If records not returned correctly.
        """
        objs: list[FakeModel] = [FakeModel(id=ID_1), FakeModel(id=ID_2)]
        mock_async_session.execute.return_value = MagicMock()
        scalars: Any = mock_async_session.execute.return_value.scalars.return_value
        scalars.all.return_value = objs
        result: list[FakeModel] = await list_items(model=mock_model)
        assert result == objs

    @pytest.mark.asyncio
    async def test_with_filters_order_offset_limit(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test list with filters, ordering, pagination.

        Verifies that complex queries with all parameters are executed once.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If query not executed with correct parameters.
        """
        mock_async_session.execute.return_value = MagicMock()
        scalars: Any = mock_async_session.execute.return_value.scalars.return_value
        scalars.all.return_value = []
        await list_items(
            model=mock_model,
            filters={"active": True},
            order_by=["-id"],
            offset=5,
            limit=10,
        )
        mock_async_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_error(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test error handling during list operation.

        Verifies that database errors raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.execute.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="list records"):
            await list_items(model=mock_model)


class TestAsyncIterateSafe:
    """Test suite for async_iterate_safe streaming operation.

    Validates asynchronous record iteration with collection and callback modes.
    """

    @pytest.mark.asyncio
    async def test_collect(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test collecting streamed records into a list.

        Verifies that records from stream are collected and returned as list.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If collected records don't match expected.
        """
        objs: list[FakeModel] = [FakeModel(id=ID_1), FakeModel(id=ID_2)]

        async def async_stream():
            yield (objs[0],)
            yield (objs[1],)

        mock_async_session.stream.return_value = async_stream()
        results: list[FakeModel] = await async_iterate_safe(
            model=mock_model, collect=True
        )
        assert results == [objs[0], objs[1]]

    @pytest.mark.asyncio
    async def test_callback(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test processing records via callback function.

        Verifies that callback is called for each streamed record.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If callback not called or results not collected.
        """
        collected: list[str] = []

        async def cb(obj: Any) -> None:
            collected.append(obj.name)

        objs: list[FakeModel] = [FakeModel(name="a"), FakeModel(name="b")]

        async def async_stream():
            for obj in objs:
                yield (obj,)

        mock_async_session.stream.return_value = async_stream()
        await async_iterate_safe(model=mock_model, callback=cb)
        assert collected == ["a", "b"]

    @pytest.mark.asyncio
    async def test_callback_and_collect_mutually_exclusive(
        self, mock_model: type[FakeModel]
    ) -> None:
        """Test that callback and collect options are mutually exclusive.

        Verifies that using both options raises ValueError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            pytest.raises.Exception: If ValueError not raised for conflicting options.
        """
        with pytest.raises(expected_exception=ValueError, match="mutually exclusive"):
            await async_iterate_safe(
                model=mock_model, callback=AsyncMock(), collect=True
            )

    @pytest.mark.asyncio
    async def test_iteration_db_error(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test error handling during streaming iteration.

        Verifies that database errors raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.stream.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="iterate records"):
            await async_iterate_safe(model=mock_model, collect=True)


class TestCount:
    """Test suite for count aggregation operation.

    Validates record counting with filtering and error handling.
    """

    @pytest.mark.asyncio
    async def test_count(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test counting records with filters.

        Verifies that count query returns the correct number of records.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            AssertionError: If count not returned correctly.
        """
        mock_async_session.execute.return_value = MagicMock()
        mock_async_session.execute.return_value.scalar_one.return_value = COUNT_EXPECTED
        assert await count(model=mock_model, filters={"active": True}) == COUNT_EXPECTED

    @pytest.mark.asyncio
    async def test_count_db_error(
        self, mock_model: type[FakeModel], mock_async_session: Mock
    ) -> None:
        """Test error handling during count operation.

        Verifies that database errors raise DatabaseError.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.
            mock_async_session (Mock): The mock AsyncSession fixture.

        Raises:
            pytest.raises.Exception: If DatabaseError not raised.
        """
        mock_async_session.execute.side_effect = SQLAlchemyError()
        with pytest.raises(expected_exception=DatabaseError, match="count records"):
            await count(model=mock_model)


class TestDeprecatedAsyncIterate:
    """Test suite for deprecated async_iterate function.

    Validates that the legacy async_iterate function issues deprecation warnings
    and delegates to async_iterate_safe.
    """

    @pytest.mark.asyncio
    async def test_deprecation_warning(self, mock_model: type[FakeModel]) -> None:
        """Test that async_iterate raises DeprecationWarning.

        Verifies that using the deprecated async_iterate function triggers
        a DeprecationWarning pointing users to async_iterate_safe.

        Args:
            mock_model (type[FakeModel]): The mock model fixture.

        Raises:
            pytest.warns.Exception: If DeprecationWarning not raised.
        """
        from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import (
            async_iterate,
        )

        with (
            patch(
                target="src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud.get_session",
                new=lambda: _fake_session_ctx(mock_session=AsyncMock()),
            ),
            pytest.warns(
                expected_warning=DeprecationWarning, match="async_iterate_safe"
            ),
        ):
            async for _ in async_iterate(model=mock_model):
                break
