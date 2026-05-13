"""Unit tests for RobustAsyncJSON5DB asynchronous JSON5 database client.

This module provides comprehensive test coverage for the RobustAsyncJSON5DB client,
including initialization, loading/saving, CRUD operations, path navigation, error
handling, auto-save functionality, atomic writes, file watching, closing, and context
manager support. The tests use pytest with asyncio support and cover both normal
operation and edge cases.

Key test areas:
    - Initialization and configuration
    - File loading and persistence
    - CRUD operations (create, read, update, delete)
    - Path navigation in nested structures (dicts and lists)
    - Error handling and custom exceptions
    - Auto-save and atomic replacement
    - File watching and reload callbacks
    - Concurrent load task synchronization
    - Context manager behavior
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import aiofiles
import aiofiles.os
import json5
import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from _asyncio import Task
    from collections.abc import AsyncGenerator

from src.plugins.nonebot_plugin_lingchu_bot.database.json5_store import (
    AtomicReplacementError,
    CallbackTypeError,
    DatabaseClosedError,
    DatabaseError,
    EmptyPathSegmentError,
    IntermediateListNoneError,
    InvalidDefaultTypeError,
    InvalidKeyPathError,
    LoadStateMismatchError,
    LoadTaskCancelledError,
    RobustAsyncJSON5DB,
    TerminalPathResolutionError,
    WatchAlreadyRunningError,
)

# ruff: noqa: PLR2004

# ---------------------------------------------------------------------------
# Constants (to avoid magic number warnings)
# ---------------------------------------------------------------------------
DEFAULT_VALUE_42: int = 42
DEFAULT_VALUE_10: int = 10
DEFAULT_VALUE_20: int = 20
DEFAULT_VALUE_3: int = 3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def tmp_db_path() -> AsyncGenerator[Path]:
    """Create a temporary JSON5 file path and clean up after test.

    Creates a temporary file using tempfile.mkstemp and yields its Path object.
    The fixture automatically removes both the database file and its temporary
    replacement file after the test completes.

    Yields:
        Path: Path object pointing to a temporary JSON5 file.

    Examples:
        >>> async def test_example(tmp_db_path: Path) -> None:
        ...     assert tmp_db_path.exists()
        ...     assert tmp_db_path.suffix == ".json5"
    """
    fd, path = tempfile.mkstemp(suffix=".json5")
    os.close(fd)
    yield Path(path)
    for p in [Path(path), Path(path).with_suffix(suffix=".tmp.json5")]:
        p.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def db(tmp_db_path: Path) -> AsyncGenerator[RobustAsyncJSON5DB]:
    """Provide an unloaded database instance.

    Creates a RobustAsyncJSON5DB instance with auto_save disabled and yields it
    for testing. The instance is automatically closed after the test completes.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Yields:
        RobustAsyncJSON5DB: An unloaded database instance ready for testing.

    Examples:
        >>> async def test_example(db: RobustAsyncJSON5DB) -> None:
        ...     assert db.is_closed is False
        ...     await db.load()
    """
    instance: RobustAsyncJSON5DB = RobustAsyncJSON5DB(
        file_path=tmp_db_path, auto_save=False
    )
    yield instance
    await instance.close()


@pytest_asyncio.fixture
async def loaded_db(tmp_db_path: Path) -> AsyncGenerator[RobustAsyncJSON5DB]:
    """Provide a loaded database instance with auto-cleanup.

    Creates a RobustAsyncJSON5DB instance with auto_save disabled, loads the
    database, and yields it for testing. The instance is automatically closed
    after the test completes.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Yields:
        RobustAsyncJSON5DB: A loaded database instance ready for testing.

    Examples:
        >>> async def test_example(loaded_db: RobustAsyncJSON5DB) -> None:
        ...     data = await loaded_db.read()
        ...     assert isinstance(data, dict)
    """
    instance: RobustAsyncJSON5DB = RobustAsyncJSON5DB(
        file_path=tmp_db_path, auto_save=False
    )
    await instance.load()
    yield instance
    await instance.close()


@pytest_asyncio.fixture
async def auto_save_db(
    tmp_db_path: Path,
) -> AsyncGenerator[RobustAsyncJSON5DB]:
    """Provide a loaded database instance with auto-save enabled.

    Creates a RobustAsyncJSON5DB instance with auto_save enabled, loads the
    database, and yields it for testing. The instance is automatically closed
    after the test completes.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Yields:
        RobustAsyncJSON5DB: A loaded database instance with auto-save enabled.

    Examples:
        >>> async def test_example(auto_save_db: RobustAsyncJSON5DB) -> None:
        ...     await auto_save_db.set(key_path="key", value="value")
    """
    instance: RobustAsyncJSON5DB = RobustAsyncJSON5DB(
        file_path=tmp_db_path, auto_save=True
    )
    await instance.load()
    yield instance
    await instance.close()


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_default_not_dict() -> None:
    """Verify that non-dict default raises InvalidDefaultTypeError.

    When initializing RobustAsyncJSON5DB with a default value that is not a
    dictionary, the constructor should raise InvalidDefaultTypeError to ensure
    data consistency and prevent runtime errors.

    Raises:
        InvalidDefaultTypeError: When default is not a dict type.

    Examples:
        >>> bad_default = [1, 2, 3]
        >>> with pytest.raises(InvalidDefaultTypeError):
        ...     RobustAsyncJSON5DB(file_path="dummy.json5", default=bad_default)
    """
    bad_default: Any = [1, 2, 3]
    with pytest.raises(expected_exception=InvalidDefaultTypeError):
        RobustAsyncJSON5DB(file_path="dummy.json5", default=bad_default)


@pytest.mark.asyncio
async def test_repr(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify __repr__ includes database file path and load state.

    The __repr__ method should provide a human-readable representation
    including the database file path and its current load state to aid
    in debugging and development.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> repr(loaded_db)
        'RobustAsyncJSON5DB(path=..., state=loaded)'
    """
    r: str = repr(loaded_db)
    assert "RobustAsyncJSON5DB" in r
    assert "loaded" in r


@pytest.mark.asyncio
async def test_is_closed(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify is_closed property correctly reflects database state.

    The is_closed property should return False for an active database
    and True after the database is explicitly closed.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> assert not loaded_db.is_closed
        >>> await loaded_db.close()
        >>> assert loaded_db.is_closed
    """
    assert not loaded_db.is_closed
    await loaded_db.close()
    assert loaded_db.is_closed


# ---------------------------------------------------------------------------
# Loading and Basic Read/Write Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_new_file(db: RobustAsyncJSON5DB) -> None:
    """Verify that loading a non-existent file initializes with default template.

    When load() is called on a non-existent file, the database should initialize
    with an empty dict (or the provided default template) without raising errors.

    Args:
        db (RobustAsyncJSON5DB): An unloaded database instance.

    Examples:
        >>> await db.load()
        >>> data = await db.read()
        >>> assert data == {}
    """
    await db.load()
    data: Any = await db.read()
    assert data == {}


@pytest.mark.asyncio
async def test_load_with_default(tmp_db_path: Path) -> None:
    """Verify that new files use the provided default template.

    When initializing a database with a custom default parameter and loading
    a non-existent file, the database should populate with the provided template.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Examples:
        >>> template = {"count": 0, "tags": []}
        >>> db = RobustAsyncJSON5DB(file_path=tmp_db_path, default=template)
        >>> await db.load()
        >>> assert await db.read() == template
    """
    template: dict[str, Any] = {"count": 0, "tags": []}
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path=tmp_db_path, default=template)
    await db.load()
    data: Any = await db.read()
    assert data == template


@pytest.mark.asyncio
async def test_load_existing_file(tmp_db_path: Path) -> None:
    """Verify that existing JSON5 files are correctly loaded.

    When loading an existing database file containing valid JSON5, the database
    should parse and populate the data correctly.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Examples:
        >>> content = {"key": "value", "num": 42}
        >>> # Write content to file
        >>> db = RobustAsyncJSON5DB(file_path=tmp_db_path)
        >>> await db.load()
        >>> assert await db.read() == content
    """
    content: dict[str, str | int] = {"key": "value", "num": DEFAULT_VALUE_42}
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write(json5.dumps(obj=content))
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path=tmp_db_path)
    await db.load()
    data: Any = await db.read()
    assert data == content


@pytest.mark.asyncio
async def test_load_empty_file(tmp_db_path: Path) -> None:
    """Verify that empty files fall back to default template.

    When loading a file with only whitespace, the database should use the
    default template instead of raising a parse error.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Examples:
        >>> # Write whitespace-only file
        >>> db = RobustAsyncJSON5DB(file_path=tmp_db_path, default={"hello": "world"})
        >>> await db.load()
        >>> assert await db.read() == {"hello": "world"}
    """
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write("   ")
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(
        file_path=tmp_db_path, default={"hello": "world"}
    )
    await db.load()
    data: Any = await db.read()
    assert data == {"hello": "world"}


@pytest.mark.asyncio
async def test_load_invalid_json(tmp_db_path: Path, caplog: Any) -> None:
    """Verify that invalid JSON falls back to default and logs warning.

    When loading a file with invalid JSON5 syntax, the database should use
    the default template and log a warning instead of crashing.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.
        caplog (Any): Pytest fixture for capturing log output.

    Examples:
        >>> # Write invalid JSON
        >>> db = RobustAsyncJSON5DB(file_path=tmp_db_path, default={"fallback": True})
        >>> await db.load()
        >>> assert await db.read() == {"fallback": True}
        >>> assert "Loading failed" in caplog.text
    """
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write("{invalid")
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(
        file_path=tmp_db_path, default={"fallback": True}
    )
    await db.load()
    data: Any = await db.read()
    assert data == {"fallback": True}
    assert "Loading failed" in caplog.text


@pytest.mark.asyncio
async def test_load_non_dict_root(tmp_db_path: Path, caplog: Any) -> None:
    """Verify that non-dict root JSON falls back to default and logs warning.

    When loading a file whose root is not a dictionary (e.g., an array or
    scalar), the database should use the default template and log a warning.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.
        caplog (Any): Pytest fixture for capturing log output.

    Examples:
        >>> # Write array to file (not dict)
        >>> db = RobustAsyncJSON5DB(file_path=tmp_db_path, default={"ok": 1})
        >>> await db.load()
        >>> assert await db.read() == {"ok": 1}
        >>> assert "Root is not a dict" in caplog.text
    """
    async with aiofiles.open(tmp_db_path, "w", encoding="utf-8") as f:
        await f.write("[1, 2, 3]")
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(
        file_path=tmp_db_path, default={"ok": 1}
    )
    await db.load()
    data: Any = await db.read()
    assert data == {"ok": 1}
    assert "Root is not a dict" in caplog.text


# ---------------------------------------------------------------------------
# Close and Context Manager Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operations_after_close(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify that operations after close raise DatabaseClosedError.

    After explicitly closing the database, any read or write operations
    should raise DatabaseClosedError to prevent silent data loss.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Raises:
        DatabaseClosedError: When attempting operations on a closed database.

    Examples:
        >>> await loaded_db.close()
        >>> with pytest.raises(DatabaseClosedError):
        ...     await loaded_db.read()
    """
    await loaded_db.close()
    with pytest.raises(expected_exception=DatabaseClosedError):
        await loaded_db.read()
    with pytest.raises(expected_exception=DatabaseClosedError):
        await loaded_db.set(key_path="x", value=1)


@pytest.mark.asyncio
async def test_async_context_manager(tmp_db_path: Path) -> None:
    """Verify async context manager auto-loads and saves on exit.

    When using the database as an async context manager, it should
    automatically load on entry and save on successful exit.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Examples:
        >>> async with RobustAsyncJSON5DB(file_path=path, auto_save=False) as db:
        ...     await db.set(key_path="k", value=100)
        >>> # File is automatically saved
    """
    path: Path = tmp_db_path
    async with RobustAsyncJSON5DB(file_path=path, auto_save=False) as db:
        await db.set(key_path="k", value=100)
    async with aiofiles.open(file=path, encoding="utf-8") as f:
        saved: dict[str, Any] = cast("dict[str, Any]", json5.loads(await f.read()))
    assert saved == {"k": 100}


@pytest.mark.asyncio
async def test_context_manager_exception(tmp_db_path: Path) -> None:
    """Verify that context manager suppresses save on exception.

    When an exception occurs within the async context manager, the database
    should not save changes (preventing data corruption), and the exception
    should propagate.

    Args:
        tmp_db_path (Path): Temporary database file path from tmp_db_path fixture.

    Examples:
        >>> with pytest.raises(RuntimeError):
        ...     async with RobustAsyncJSON5DB(file_path=path, auto_save=False) as db:
        ...         await db.set(key_path="keep", value=1)
        ...         raise RuntimeError("boom")
    """
    path: Path = tmp_db_path
    with pytest.raises(RuntimeError):
        async with RobustAsyncJSON5DB(file_path=path, auto_save=False) as db:
            await db.set(key_path="keep", value=1)
            raise RuntimeError("boom")
    async with aiofiles.open(path, encoding="utf-8") as f:
        content: str = await f.read()
    assert "keep" not in content


# ---------------------------------------------------------------------------
# Read and Atomic Read Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_root(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify reading the root object returns full database.

    The read() method without a key_path should return the entire database
    object as a single dictionary.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="a", value=1)
        >>> data = await loaded_db.read()
        >>> assert data == {"a": 1}
    """
    await loaded_db.set(key_path="a", value=1)
    data: Any = await loaded_db.read()
    assert data == {"a": 1}


@pytest.mark.asyncio
async def test_read_nested(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify reading nested paths using dot notation.

    Deep nested values should be accessible via dot-separated paths
    like "x.y.z" to navigate through nested dictionaries.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="x.y.z", value="deep")
        >>> val = await loaded_db.read(key_path="x.y.z")
        >>> assert val == "deep"
    """
    await loaded_db.set(key_path="x.y.z", value="deep")
    val: Any = await loaded_db.read(key_path="x.y.z")
    assert val == "deep"


@pytest.mark.asyncio
async def test_read_default_value(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify reading non-existent paths returns default value.

    When reading a path that does not exist, the read() method should return
    the provided default value instead of raising an error.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> val = await loaded_db.read(key_path="no.such", default=42)
        >>> assert val == 42
    """
    val: Any = await loaded_db.read(key_path="no.such", default=DEFAULT_VALUE_42)
    assert val == DEFAULT_VALUE_42


@pytest.mark.asyncio
async def test_read_use_deepcopy(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify deep copy returns independent copies of data.

    When use_deepcopy=True (default), multiple reads should return independent
    copies so modifications to one don't affect others.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="mylist", value=[1, 2, 3])
        >>> copy1 = await loaded_db.read(key_path="mylist")
        >>> copy2 = await loaded_db.read(key_path="mylist")
        >>> assert copy1 == copy2
        >>> assert copy1 is not copy2
    """
    await loaded_db.set(key_path="mylist", value=[1, 2, 3])
    copy1: Any = await loaded_db.read(key_path="mylist")
    copy2: Any = await loaded_db.read(key_path="mylist")
    assert copy1 == [1, 2, 3]
    assert copy1 is not copy2


@pytest.mark.asyncio
async def test_atomic_read(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify atomic_read returns deep copy maintaining data consistency.

    atomic_read() should return a deep copy of the data, ensuring that
    modifications to the returned copy don't affect the database state.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="deep", value={"nested": {"a": 1}})
        >>> val = await loaded_db.atomic_read(key_path="deep")
        >>> val["nested"]["a"] = 999
        >>> orig = await loaded_db.read(key_path="deep")
        >>> assert orig["nested"]["a"] == 1
    """
    await loaded_db.set(key_path="deep", value={"nested": {"a": 1}})
    val: Any = await loaded_db.atomic_read(key_path="deep")
    assert val == {"nested": {"a": 1}}
    val["nested"]["a"] = 999
    orig: Any = await loaded_db.read(key_path="deep")
    assert orig["nested"]["a"] == 1


# ---------------------------------------------------------------------------
# CRUD Tests: Set, Create, Update, Delete, Exists, Clear
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_new_key(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify setting a new key creates the nested path structure.

    The set() method should create all intermediate dictionaries as needed
    to accommodate the given key path.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="new.key", value="hi")
        >>> assert await loaded_db.read(key_path="new.key") == "hi"
    """
    await loaded_db.set(key_path="new.key", value="hi")
    assert await loaded_db.read(key_path="new.key") == "hi"


@pytest.mark.asyncio
async def test_set_overwrite(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify set() overwrites existing values.

    When setting a key that already exists, the new value should completely
    replace the old value.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="k", value=1)
        >>> await loaded_db.set(key_path="k", value=2)
        >>> assert await loaded_db.read(key_path="k") == 2
    """
    await loaded_db.set(key_path="k", value=1)
    await loaded_db.set(key_path="k", value=2)
    assert await loaded_db.read(key_path="k") == 2


@pytest.mark.asyncio
async def test_create_success(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify create() succeeds when key doesn't exist and returns True.

    The create() method should create a new key-value pair and return True
    only when the key did not previously exist.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Returns:
        bool: True if key was created, False if it already existed.

    Examples:
        >>> result = await loaded_db.create(key_path="alpha", value=10)
        >>> assert result is True
        >>> assert await loaded_db.read(key_path="alpha") == 10
    """
    result: bool = await loaded_db.create(key_path="alpha", value=DEFAULT_VALUE_10)
    assert result is True
    assert await loaded_db.read(key_path="alpha") == DEFAULT_VALUE_10


@pytest.mark.asyncio
async def test_create_already_exists(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify create() fails when key exists and returns False.

    When the key already exists, create() should return False and not modify
    the existing value.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Returns:
        bool: False when key already existed.

    Examples:
        >>> await loaded_db.set(key_path="beta", value=20)
        >>> result = await loaded_db.create(key_path="beta", value=30)
        >>> assert result is False
        >>> assert await loaded_db.read(key_path="beta") == 20
    """
    await loaded_db.set(key_path="beta", value=DEFAULT_VALUE_20)
    result: bool = await loaded_db.create(key_path="beta", value=30)
    assert result is False
    assert await loaded_db.read(key_path="beta") == DEFAULT_VALUE_20


@pytest.mark.asyncio
async def test_update_existing(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify update() succeeds for existing keys and returns True.

    The update() method should modify an existing key and return True
    only when the key already existed.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Returns:
        bool: True if key existed and was updated, False otherwise.

    Examples:
        >>> await loaded_db.set(key_path="gamma", value=1)
        >>> result = await loaded_db.update(key_path="gamma", value=2)
        >>> assert result is True
        >>> assert await loaded_db.read(key_path="gamma") == 2
    """
    await loaded_db.set(key_path="gamma", value=1)
    result: bool = await loaded_db.update(key_path="gamma", value=2)
    assert result is True
    assert await loaded_db.read(key_path="gamma") == 2


@pytest.mark.asyncio
async def test_update_nonexistent(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify update() fails for non-existent keys and returns False.

    When updating a key that doesn't exist, update() should return False
    and not create the key.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Returns:
        bool: False when key doesn't exist.

    Examples:
        >>> result = await loaded_db.update(key_path="delta", value=1)
        >>> assert result is False
    """
    result: bool = await loaded_db.update(key_path="delta", value=1)
    assert result is False


@pytest.mark.asyncio
async def test_delete(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify delete() removes existing keys and returns True.

    The delete() method should remove a key-value pair and return True
    when the key existed.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Returns:
        bool: True if key existed and was deleted, False otherwise.

    Examples:
        >>> await loaded_db.set(key_path="del.me", value="bye")
        >>> result = await loaded_db.delete(key_path="del.me")
        >>> assert result is True
        >>> assert not await loaded_db.exists(key_path="del.me")
    """
    await loaded_db.set(key_path="del.me", value="bye")
    result: bool = await loaded_db.delete(key_path="del.me")
    assert result is True
    assert not await loaded_db.exists(key_path="del.me")


@pytest.mark.asyncio
async def test_delete_nonexistent(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify delete() returns False for non-existent keys.

    When deleting a key that doesn't exist, delete() should return False
    without raising an error.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Returns:
        bool: False when key doesn't exist.

    Examples:
        >>> result = await loaded_db.delete(key_path="nope")
        >>> assert result is False
    """
    result: bool = await loaded_db.delete(key_path="nope")
    assert result is False


@pytest.mark.asyncio
async def test_delete_list_shifts(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify deleting list items shifts remaining elements correctly.

    When deleting an item from a list, remaining items should shift down
    (array indices decrease) to fill the gap.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="items", value=["a", "b", "c"])
        >>> await loaded_db.delete(key_path="items.1")
        >>> lst = await loaded_db.read(key_path="items")
        >>> assert lst == ["a", "c"]
    """
    await loaded_db.set(key_path="items", value=["a", "b", "c"])
    await loaded_db.delete(key_path="items.1")
    lst: Any = await loaded_db.read(key_path="items")
    assert lst == ["a", "c"]


@pytest.mark.asyncio
async def test_exists(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify exists() correctly reports key presence.

    The exists() method should return True for existing keys and False
    for non-existent keys.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Returns:
        bool: True if key exists, False otherwise.

    Examples:
        >>> await loaded_db.set(key_path="e.x", value=1)
        >>> assert await loaded_db.exists(key_path="e.x") is True
        >>> assert await loaded_db.exists(key_path="e.y") is False
    """
    await loaded_db.set(key_path="e.x", value=1)
    assert await loaded_db.exists(key_path="e.x") is True
    assert await loaded_db.exists(key_path="e.y") is False


@pytest.mark.asyncio
async def test_clear(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify clear() removes all database contents.

    The clear() method should remove all key-value pairs, leaving an empty
    dictionary as the database state.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="x", value=1)
        >>> await loaded_db.clear()
        >>> assert await loaded_db.read() == {}
    """
    await loaded_db.set(key_path="x", value=1)
    await loaded_db.clear()
    assert await loaded_db.read() == {}


# ---------------------------------------------------------------------------
# Batch Set Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_batch(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify set_batch() applies multiple updates atomically.

    The set_batch() method should apply a dictionary of key-value pairs
    in a single atomic operation.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="a", value=0)
        >>> updates = {"b.c": 1, "d": [10, 20]}
        >>> await loaded_db.set_batch(updates)
        >>> assert await loaded_db.read(key_path="b.c") == 1
    """
    await loaded_db.set(key_path="a", value=0)
    updates: dict[str, int | list[int]] = {"b.c": 1, "d": [10, 20]}
    await loaded_db.set_batch(updates)
    assert await loaded_db.read(key_path="b.c") == 1
    assert await loaded_db.read(key_path="d") == [10, 20]
    assert await loaded_db.read(key_path="a") == 0


@pytest.mark.asyncio
async def test_set_batch_empty(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify set_batch() with empty dict does nothing.

    Calling set_batch() with an empty dictionary should not modify the database.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set_batch(updates={})
        >>> assert await loaded_db.read() == {}
    """
    await loaded_db.set_batch(updates={})
    assert await loaded_db.read() == {}


@pytest.mark.asyncio
async def test_set_batch_atomic(
    auto_save_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """Verify set_batch() is atomic with auto_save enabled.

    When auto_save is enabled, if any key in the batch is invalid, the entire
    batch should fail and no changes should be persisted.

    Args:
        auto_save_db (RobustAsyncJSON5DB): A loaded database with auto-save enabled.
        tmp_db_path (Path): Temporary database file path.

    Raises:
        InvalidKeyPathError: When batch contains invalid key path.

    Examples:
        >>> await auto_save_db.set(key_path="x", value=1)
        >>> with pytest.raises(InvalidKeyPathError):
        ...     await auto_save_db.set_batch(updates={"y": 2, "": 3})
    """
    await auto_save_db.set(key_path="x", value=1)
    with pytest.raises(expected_exception=InvalidKeyPathError):
        await auto_save_db.set_batch(updates={"y": 2, "": DEFAULT_VALUE_3})
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        content: dict[str, Any] = cast("dict[str, Any]", json5.loads(await f.read()))
    assert content == {"x": 1}


# ---------------------------------------------------------------------------
# Auto-Save Behavior Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_save_writes_immediately(
    auto_save_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """Verify auto_save=True persists changes immediately to disk.

    When auto_save is enabled, any modification should be immediately
    written to the file.

    Args:
        auto_save_db (RobustAsyncJSON5DB): A loaded database with auto-save enabled.
        tmp_db_path (Path): Temporary database file path.

    Examples:
        >>> await auto_save_db.set(key_path="instant", value=1)
        >>> # File is immediately updated
    """
    await auto_save_db.set(key_path="instant", value=1)
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        saved: dict[str, Any] = cast("dict[str, Any]", json5.loads(await f.read()))
    assert saved == {"instant": 1}


@pytest.mark.asyncio
async def test_no_auto_save(loaded_db: RobustAsyncJSON5DB, tmp_db_path: Path) -> None:
    """Verify auto_save=False requires explicit save() call.

    When auto_save is disabled, changes should not be persisted until
    save() is explicitly called.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database without auto-save.
        tmp_db_path (Path): Temporary database file path.

    Examples:
        >>> await loaded_db.set(key_path="later", value=1)
        >>> # Changes not yet in file
        >>> await loaded_db.save()
        >>> # Now in file
    """
    await loaded_db.set(key_path="later", value=1)
    if await aiofiles.os.path.exists(tmp_db_path):
        async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
            content: str = await f.read()
        assert "later" not in content
    await loaded_db.save()
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        saved: dict[str, Any] = cast("dict[str, Any]", json5.loads(await f.read()))
    assert saved == {"later": 1}


# ---------------------------------------------------------------------------
# Path Navigation Tests: Dictionary/List Mix, Indexing, Error Cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_through_list(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify navigating through list indices in dot notation.

    Paths can use list indices (e.g., "outer.0.name") to access items
    within lists.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set("outer", [{}])
        >>> await loaded_db.set(key_path="outer.0.name", value="Alice")
        >>> assert await loaded_db.read(key_path="outer.0.name") == "Alice"
    """
    await loaded_db.set("outer", [{}])
    await loaded_db.set(key_path="outer.0.name", value="Alice")
    assert await loaded_db.read(key_path="outer.0.name") == "Alice"
    data: Any = await loaded_db.read()
    assert data == {"outer": [{"name": "Alice"}]}


@pytest.mark.asyncio
async def test_path_list_index_none_placeholder(
    loaded_db: RobustAsyncJSON5DB,
) -> None:
    """Verify None placeholder list items cannot be drilled into.

    When a list contains None as a placeholder, attempting to navigate
    through it should raise IntermediateListNoneError.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Raises:
        IntermediateListNoneError: When drilling into None list item.

    Examples:
        >>> await loaded_db.set(key_path="mylist", value=[None])
        >>> with pytest.raises(IntermediateListNoneError):
        ...     await loaded_db.set(key_path="mylist.0.key", value=1)
    """
    await loaded_db.set(key_path="mylist", value=[None])
    with pytest.raises(expected_exception=IntermediateListNoneError):
        await loaded_db.set(key_path="mylist.0.key", value=1)


@pytest.mark.asyncio
async def test_parent_path_resolution_error(
    loaded_db: RobustAsyncJSON5DB,
) -> None:
    """Verify parent node type mismatch raises TerminalPathResolutionError.

    When a parent node's type doesn't support the operation, the database
    should raise TerminalPathResolutionError.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Raises:
        TerminalPathResolutionError: When parent type doesn't match path operation.

    Examples:
        >>> await loaded_db.set(key_path="val", value=42)
        >>> with pytest.raises(TerminalPathResolutionError):
        ...     await loaded_db.set(key_path="val.sub", value=1)
    """
    await loaded_db.set(key_path="val", value=DEFAULT_VALUE_42)
    with pytest.raises(expected_exception=TerminalPathResolutionError):
        await loaded_db.set(key_path="val.sub", value=1)


@pytest.mark.asyncio
async def test_terminal_path_resolution_error(
    loaded_db: RobustAsyncJSON5DB,
) -> None:
    """Verify target container type mismatch raises TerminalPathResolutionError.

    When the terminal container (dict or list) doesn't support the requested
    key/index, the database should raise TerminalPathResolutionError.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Raises:
        TerminalPathResolutionError: When terminal type doesn't support key.

    Examples:
        >>> await loaded_db.set(key_path="lst", value=[1, 2])
        >>> with pytest.raises(TerminalPathResolutionError):
        ...     await loaded_db.set(key_path="lst.key", value=1)
    """
    await loaded_db.set(key_path="lst", value=[1, 2])
    with pytest.raises(expected_exception=TerminalPathResolutionError):
        await loaded_db.set(key_path="lst.key", value=1)


@pytest.mark.asyncio
async def test_empty_path_segment() -> None:
    """Verify empty path segments raise EmptyPathSegmentError.

    Paths with consecutive dots (e.g., "a..b") contain empty segments
    and should raise EmptyPathSegmentError.

    Args:
        None

    Raises:
        EmptyPathSegmentError: When path contains empty segment.

    Examples:
        >>> db = RobustAsyncJSON5DB(file_path="dummy.json5")
        >>> with pytest.raises(EmptyPathSegmentError):
        ...     db._validate_path(key_path="a..b")
    """
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path="dummy.json5")
    with pytest.raises(expected_exception=EmptyPathSegmentError):
        db._validate_path(key_path="a..b")


@pytest.mark.asyncio
async def test_invalid_key_path() -> None:
    """Verify non-string or empty key paths raise InvalidKeyPathError.

    The key_path parameter must be a non-empty string. Non-string or empty
    paths should raise InvalidKeyPathError.

    Args:
        None

    Raises:
        InvalidKeyPathError: When key_path is invalid.

    Examples:
        >>> db = RobustAsyncJSON5DB(file_path="dummy.json5")
        >>> with pytest.raises(InvalidKeyPathError):
        ...     db._validate_path(key_path=None)
    """
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path="dummy.json5")
    bad_path: Any = None
    with pytest.raises(expected_exception=InvalidKeyPathError):
        db._validate_path(key_path=bad_path)
    with pytest.raises(expected_exception=InvalidKeyPathError):
        db._validate_path(key_path="")


@pytest.mark.asyncio
async def test_read_nonexistent_list_index(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify reading non-existent list index returns default value.

    When reading a list index that doesn't exist, the read() method should
    return the provided default value.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="arr", value=[10])
        >>> val = await loaded_db.read(key_path="arr.5", default="missing")
        >>> assert val == "missing"
    """
    await loaded_db.set(key_path="arr", value=[10])
    val: Any = await loaded_db.read(key_path="arr.5", default="missing")
    assert val == "missing"


# ---------------------------------------------------------------------------
# Save and Atomic Replacement Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_creates_parent_directory(tmp_db_path: Path) -> None:
    """Verify save() creates parent directories if they don't exist.

    When saving to a path whose parent directory doesn't exist, the save()
    method should create the necessary directory structure.

    Args:
        tmp_db_path (Path): Temporary database file path.

    Examples:
        >>> nested_dir = tmp_db_path.parent / "subdir" / "data.json5"
        >>> db = RobustAsyncJSON5DB(file_path=nested_dir)
        >>> await db.load()
        >>> await db.set(key_path="x", value=1)
        >>> await db.save()
        >>> assert nested_dir.exists()
    """
    nested_dir: Path = tmp_db_path.parent / "subdir" / "data.json5"
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path=nested_dir)
    await db.load()
    await db.set(key_path="x", value=1)
    await db.save()
    assert await aiofiles.os.path.exists(nested_dir)
    await db.close()
    shutil.rmtree(path=nested_dir.parent)


@pytest.mark.asyncio
async def test_atomic_replace_simulation(
    auto_save_db: RobustAsyncJSON5DB,
    tmp_db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify atomic replacement reverts on failure.

    When an atomic file replacement fails, the original file should remain
    unchanged and an AtomicReplacementError should be raised.

    Args:
        auto_save_db (RobustAsyncJSON5DB): A loaded database with auto-save enabled.
        tmp_db_path (Path): Temporary database file path.
        monkeypatch (pytest.MonkeyPatch): Pytest fixture for mocking.

    Raises:
        AtomicReplacementError: When atomic replacement fails.

    Examples:
        >>> # Simulate atomic replacement failure
        >>> with pytest.raises(AtomicReplacementError):
        ...     await auto_save_db.set(key_path="new_key", value="fail")
    """
    await auto_save_db.set(key_path="existing", value="original")
    await asyncio.sleep(0.01)

    async with aiofiles.open(tmp_db_path, encoding="utf-8") as f:
        original_content: dict[str, str] = cast(
            "dict[str, str]", json5.loads(await f.read())
        )

    async def fake_replace(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("simulated")

    monkeypatch.setattr(aiofiles.os, "replace", fake_replace)

    with pytest.raises(AtomicReplacementError):
        await auto_save_db.set(key_path="new_key", value="fail")

    async with aiofiles.open(tmp_db_path, encoding="utf-8") as f:
        saved: dict[str, str] = cast("dict[str, str]", json5.loads(await f.read()))
    assert saved == original_content


# ---------------------------------------------------------------------------
# Reload Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reload_from_disk(
    loaded_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """Verify reload() reloads data from disk after external modification.

    After an external process modifies the file, reload() should fetch the
    updated data from disk and refresh the in-memory state.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.
        tmp_db_path (Path): Temporary database file path.

    Examples:
        >>> await loaded_db.set(key_path="v1", value=1)
        >>> # External modification
        >>> await loaded_db.reload()
        >>> assert await loaded_db.read() == {"v2": 2}
    """
    await loaded_db.set(key_path="v1", value=1)
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write(json5.dumps(obj={"v2": 2}))
    await loaded_db.reload()
    data: Any = await loaded_db.read()
    assert data == {"v2": 2}
    assert await loaded_db.exists(key_path="v1") is False


@pytest.mark.asyncio
async def test_reload_with_callback(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify reload() invokes callback after completion.

    The reload() method should accept an optional callback parameter and
    invoke it after reloading completes.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> called = False
        >>> async def on_reload() -> None:
        ...     global called
        ...     called = True
        >>> await loaded_db.reload(callback=on_reload)
        >>> assert called is True
    """
    called: bool = False

    async def on_reload() -> None:
        nonlocal called
        called = True

    await loaded_db.reload(callback=on_reload)
    assert called is True


@pytest.mark.asyncio
async def test_reload_invalid_callback(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify reload() rejects non-async callbacks.

    When passing a non-async callback to reload(), it should raise
    CallbackTypeError.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Raises:
        CallbackTypeError: When callback is not async.

    Examples:
        >>> def not_async_callback() -> None:
        ...     pass
        >>> with pytest.raises(CallbackTypeError):
        ...     await loaded_db.reload(callback=not_async_callback)
    """

    def not_async_callback() -> None:
        return

    with pytest.raises(expected_exception=CallbackTypeError):
        await loaded_db.reload(callback=not_async_callback)  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# File Watch Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_detects_external_change(
    loaded_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """Verify watch() detects external file changes and invokes callback.

    The watch() method should monitor the database file for changes and
    automatically reload + invoke the callback when external modifications
    are detected.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.
        tmp_db_path (Path): Temporary database file path.

    Examples:
        >>> async def on_change() -> None:
        ...     pass
        >>> await loaded_db.watch(callback=on_change, interval=0.05)
        >>> # File is modified externally
        >>> # Callback is invoked automatically
    """
    callback_event: asyncio.Event = asyncio.Event()

    async def on_change() -> None:
        callback_event.set()

    await loaded_db.watch(callback=on_change, interval=0.05)

    await asyncio.sleep(delay=0.1)

    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write(json5.dumps(obj={"new": "data"}))

    try:
        await asyncio.wait_for(fut=callback_event.wait(), timeout=2.0)
    except TimeoutError:
        pytest.fail(reason="Watch callback was not triggered")

    data: Any = await loaded_db.read()
    assert data == {"new": "data"}

    await loaded_db.close()


@pytest.mark.asyncio
async def test_watch_already_running(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify watch() raises error when already running.

    Calling watch() multiple times should raise WatchAlreadyRunningError
    to prevent duplicate watchers.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Raises:
        WatchAlreadyRunningError: When watch already running.

    Examples:
        >>> await loaded_db.watch(interval=0.5)
        >>> with pytest.raises(WatchAlreadyRunningError):
        ...     await loaded_db.watch(interval=0.5)
    """
    await loaded_db.watch(interval=0.5)
    with pytest.raises(expected_exception=WatchAlreadyRunningError):
        await loaded_db.watch(interval=0.5)
    await loaded_db.close()


# ---------------------------------------------------------------------------
# Concurrent Load Guarantee Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_load_calls_one_load_task(
    db: RobustAsyncJSON5DB, mocker: Any
) -> None:
    """Verify concurrent load/ensure_loaded calls only start one load task.

    Multiple concurrent calls to load() or ensure_loaded() should be
    synchronized so only a single actual load task runs, then all callers
    wait for that same task to complete.

    Args:
        db (RobustAsyncJSON5DB): An unloaded database instance.
        mocker (Any): Pytest-mock fixture for spying on calls.

    Examples:
        >>> await asyncio.gather(db.load(), db.load(), db.load())
        >>> # Only one _unsafe_load call made
    """
    call_count: int = 0
    original_unsafe_load = RobustAsyncJSON5DB._unsafe_load

    async def patched_unsafe_load(
        self_: RobustAsyncJSON5DB, default_copy: dict[str, Any]
    ) -> None:
        nonlocal call_count
        call_count += 1
        await original_unsafe_load(self_, default_copy)

    mocker.patch.object(RobustAsyncJSON5DB, "_unsafe_load", new=patched_unsafe_load)
    await asyncio.gather(db.load(), db.load(), db.load())
    assert call_count == 1


# ---------------------------------------------------------------------------
# Close Task Cancellation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_cancels_load_task() -> None:
    """Verify close() cancels in-progress load tasks.

    When the database is closed while a load task is in progress, the
    close() method should cancel the pending load task.

    Args:
        None

    Examples:
        >>> db = RobustAsyncJSON5DB(file_path="never_used.json5")
        >>> task = asyncio.create_task(db.load())
        >>> await asyncio.sleep(0.05)
        >>> await db.close()
        >>> assert task.cancelled() or task.done()
    """
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path="never_used.json5")

    async def stuck_load(_self: Any) -> None:
        await asyncio.Event().wait()

    with patch.object(target=RobustAsyncJSON5DB, attribute="_do_load", new=stuck_load):
        task: Task[None] = asyncio.create_task(coro=db.load())
        await asyncio.sleep(delay=0.05)
        await db.close()
        assert task.cancelled() or task.done()


# ---------------------------------------------------------------------------
# Custom Exception Hierarchy Tests
# ---------------------------------------------------------------------------


def test_exception_hierarchy() -> None:
    """Verify custom exception inheritance relationships.

    All custom database exceptions should inherit from DatabaseError to
    allow unified exception handling.

    Returns:
        None

    Examples:
        >>> assert issubclass(DatabaseClosedError, DatabaseError)
        >>> assert issubclass(InvalidKeyPathError, DatabaseError)
    """
    assert issubclass(DatabaseClosedError, DatabaseError)
    assert issubclass(InvalidKeyPathError, DatabaseError)
    assert issubclass(AtomicReplacementError, DatabaseError)
    assert issubclass(InvalidDefaultTypeError, DatabaseError)


# ---------------------------------------------------------------------------
# Edge Case Tests: Deep Copy, Explicit Save Without Auto-Save
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_deepcopy_scalar(loaded_db: RobustAsyncJSON5DB) -> None:
    """Verify deep copy doesn't affect scalar values.

    Deep copying scalar types (int, str, bool, etc.) should have no observable
    effect since they are immutable.

    Args:
        loaded_db (RobustAsyncJSON5DB): A loaded database instance.

    Examples:
        >>> await loaded_db.set(key_path="num", value=42)
        >>> val = await loaded_db.read(key_path="num", use_deepcopy=True)
        >>> assert val == 42
    """
    await loaded_db.set(key_path="num", value=DEFAULT_VALUE_42)
    val: Any = await loaded_db.read(key_path="num", use_deepcopy=True)
    assert val == DEFAULT_VALUE_42


@pytest.mark.asyncio
async def test_auto_save_create_update_return(
    auto_save_db: RobustAsyncJSON5DB,
) -> None:
    """Verify create/update return correct bool with auto_save enabled.

    With auto_save enabled, create() and update() should still return
    correct boolean values indicating success or failure.

    Args:
        auto_save_db (RobustAsyncJSON5DB): A loaded database with auto-save enabled.

    Returns:
        bool: True for successful operations, False for failures.

    Examples:
        >>> res = await auto_save_db.create(key_path="foo", value=1)
        >>> assert res is True
        >>> res = await auto_save_db.create(key_path="foo", value=2)
        >>> assert res is False
    """
    res: bool = await auto_save_db.create(key_path="foo", value=1)
    assert res is True
    res: bool = await auto_save_db.create(key_path="foo", value=2)
    assert res is False
    res: bool = await auto_save_db.update(key_path="bar", value=DEFAULT_VALUE_3)
    assert res is False
    await auto_save_db.set(key_path="bar", value=0)
    res: bool = await auto_save_db.update(key_path="bar", value=DEFAULT_VALUE_3)
    assert res is True
    assert await auto_save_db.read(key_path="bar") == DEFAULT_VALUE_3


@pytest.mark.asyncio
async def test_set_batch_with_auto_save(
    auto_save_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """Verify batch updates persist immediately with auto_save enabled.

    When auto_save is enabled, set_batch() should persist all updates
    immediately to the file.

    Args:
        auto_save_db (RobustAsyncJSON5DB): A loaded database with auto-save enabled.
        tmp_db_path (Path): Temporary database file path.

    Examples:
        >>> await auto_save_db.set_batch(updates={"a": 1, "b.c": 2})
        >>> # File is immediately updated
    """
    await auto_save_db.set_batch(updates={"a": 1, "b.c": 2})
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        content: dict[str, Any] = cast("dict[str, Any]", json5.loads(await f.read()))
    assert content == {"a": 1, "b": {"c": 2}}


# ---------------------------------------------------------------------------
# Load Task Cancellation Edge Cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_task_cancelled_error() -> None:
    """Verify LoadTaskCancelledError raised when load task is cancelled.

    When a load task is cancelled (not due to close()), attempting to await
    it should raise LoadTaskCancelledError.

    Args:
        None

    Raises:
        LoadTaskCancelledError: When load task is cancelled.

    Examples:
        >>> db = RobustAsyncJSON5DB(file_path="some_file.json5")
        >>> await db._start_load_task()
        >>> if db._load_task:
        ...     db._load_task.cancel()
        >>> with pytest.raises(LoadTaskCancelledError):
        ...     await db._await_load_task()
    """
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path="some_file.json5")

    async def never_finish(_self: Any) -> None:
        await asyncio.Event().wait()

    with patch.object(
        target=RobustAsyncJSON5DB, attribute="_do_load", new=never_finish
    ):
        await db._start_load_task()
        if db._load_task is not None:
            db._load_task.cancel()
        with pytest.raises(expected_exception=LoadTaskCancelledError):
            await db._await_load_task()
    await db.close()


@pytest.mark.asyncio
async def test_load_state_mismatch() -> None:
    """Verify LoadStateMismatchError when load completes but _loaded is False.

    If a load task completes without setting _loaded to True, this indicates
    an internal state corruption and should raise LoadStateMismatchError.

    Args:
        None

    Raises:
        LoadStateMismatchError: When load state is inconsistent.

    Examples:
        >>> db = RobustAsyncJSON5DB(file_path="x.json5")
        >>> # Mock _unsafe_load to not set _loaded
        >>> with pytest.raises(LoadStateMismatchError):
        ...     await db._ensure_loaded()
    """
    db: RobustAsyncJSON5DB = RobustAsyncJSON5DB(file_path="x.json5")

    async def fake_unsafe_load(_self: Any, _default_copy: dict[str, Any]) -> None:
        pass

    with (
        patch.object(
            target=RobustAsyncJSON5DB,
            attribute="_unsafe_load",
            new=fake_unsafe_load,
        ),
        pytest.raises(expected_exception=LoadStateMismatchError),
    ):
        await db._ensure_loaded()
    await db.close()
