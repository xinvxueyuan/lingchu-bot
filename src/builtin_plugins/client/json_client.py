from __future__ import annotations

import asyncio
import contextlib
import logging
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

import aiofiles
import aiofiles.os
import json5

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from types import TracebackType

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for JSON5 database errors."""


class InvalidDefaultTypeError(TypeError, DatabaseError):
    def __init__(self, actual_type: type[Any]) -> None:
        super().__init__(f"default must be a dict, got {actual_type}")


class DatabaseClosedError(RuntimeError, DatabaseError):
    def __init__(self) -> None:
        super().__init__("Database is closed")


class InvalidKeyPathError(ValueError, DatabaseError):
    def __init__(self, key_path: Any) -> None:
        super().__init__(f"Key path must be a non-empty string: {key_path!r}")


class EmptyPathSegmentError(ValueError, DatabaseError):
    def __init__(self, key_path: str) -> None:
        super().__init__(
            f"Invalid key path: {key_path!r}, empty segments are not allowed"
        )


class LoadTaskCancelledError(RuntimeError, DatabaseError):
    def __init__(self) -> None:
        super().__init__("Load task was unexpectedly cancelled")


class LoadStateMismatchError(RuntimeError, DatabaseError):
    def __init__(self) -> None:
        super().__init__("Loading completed but database not marked as loaded")


class CallbackTypeError(TypeError, DatabaseError):
    def __init__(self) -> None:
        super().__init__("callback must be an async function (or None)")


class AtomicReplacementError(RuntimeError, DatabaseError):
    def __init__(self) -> None:
        super().__init__("Atomic file replacement failed")


class WatchAlreadyRunningError(RuntimeError, DatabaseError):
    def __init__(self) -> None:
        super().__init__("A watcher is already running")


class IntermediateListNoneError(ValueError, DatabaseError):
    def __init__(self, index: int, path: str) -> None:
        super().__init__(
            f"Cannot create intermediate dictionary at list index {index} "
            f"(None placeholder). Provide explicit structure before "
            f"accessing through a non-numeric key. Path: {path}"
        )


class ParentPathResolutionError(ValueError, DatabaseError):
    def __init__(self, segment: str, actual_type: str, path: str) -> None:
        super().__init__(
            f"Path resolution failed: parent at segment '{segment}' is "
            f"{actual_type}, cannot descend. Path: {path}"
        )


class TerminalPathResolutionError(ValueError, DatabaseError):
    def __init__(self, actual_type: str, target_key: str, path: str) -> None:
        super().__init__(
            f"Terminal navigation failed: container type {actual_type} does "
            f"not support key '{target_key}'. Path: {path}"
        )


class RobustAsyncJSON5DB:
    """
    Asynchronous JSON5 file database with atomic writes and nested key support.

    Supports dict/list path navigation, optional file watching, and explicit close.
    Stores only JSON5-compatible objects: dict, list, str, int, float, bool, None.

    Numeric segments like "items.0" are list indices only when non-negative.
    Deleting a list index shifts following elements.

    Atomic save writes to .tmp.json5 first, then replaces the main file.
    Temporary files are cleaned on load and close.

    File watcher can race with concurrent writers. Coordinate writes carefully.

    With auto_save=True each write deep copies data, serializes, and atomically
    commits disk then memory. This is safe but slower for frequent updates.

    Heavy work is offloaded so the event loop stays responsive unless atomic_read()
    is used, which deep-copies under lock for stronger consistency.
    """

    __slots__ = (
        "_closed",
        "_data",
        "_load_lock",
        "_load_task",
        "_loaded",
        "_lock",
        "_raw_default",
        "_watch_mtime",
        "_watch_task",
        "auto_save",
        "ensure_ascii",
        "file_path",
        "indent",
        "temp_file_path",
    )

    def __init__(
        self,
        file_path: str | Path,
        *,
        auto_save: bool = True,
        indent: int = 2,
        ensure_ascii: bool = False,
        default: dict[str, Any] | None = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.temp_file_path = self.file_path.with_suffix(".tmp.json5")
        self.auto_save = auto_save
        self.indent = indent
        self.ensure_ascii = ensure_ascii

        if default is not None and not isinstance(default, dict):
            raise InvalidDefaultTypeError(type(default))
        # Decouple internal state from mutable objects passed by caller.
        self._raw_default: dict[str, Any] = (
            deepcopy(default) if default is not None else {}
        )

        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()  # protects _data and _loaded
        self._loaded = False
        self._closed = False  # prevents operations after close
        self._load_lock = asyncio.Lock()  # ensures single loading task
        self._load_task: asyncio.Task | None = None
        self._watch_task: asyncio.Task | None = None
        self._watch_mtime: float = 0.0

    # ------------------------------------------------------------------
    # Properties & representation
    # ------------------------------------------------------------------

    @property
    def is_closed(self) -> bool:
        """Return True if the database has been closed."""
        return self._closed

    def __repr__(self) -> str:
        status = (
            "closed" if self._closed else ("loaded" if self._loaded else "not loaded")
        )
        return f"<RobustAsyncJSON5DB path={self.file_path!r} status={status}>"

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def _get_fresh_default_copy(self) -> dict[str, Any]:
        """Asynchronously return a fresh deep-copied default template."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, deepcopy, self._raw_default)

    async def _cleanup_temp_file_async(self) -> None:
        if await aiofiles.os.path.exists(self.temp_file_path):
            with contextlib.suppress(OSError):
                await aiofiles.os.remove(self.temp_file_path)

    async def close(self) -> None:
        """Stop tasks, clean temp file, and mark database as closed."""
        if self._closed:
            return
        self._closed = True

        # Cancel pending load to avoid post-close state changes.
        if self._load_task and not self._load_task.done():
            self._load_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._load_task

        # Stop file watcher if active
        if self._watch_task is not None and not self._watch_task.done():
            self._watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watch_task
        self._watch_task = None

        # Delete temp file asynchronously, ignore errors if already gone
        with contextlib.suppress(Exception):
            await self._cleanup_temp_file_async()

    async def __aenter__(self) -> Self:
        await self.load()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        del exc_val, exc_tb
        try:
            # auto_save=True writes on every change; manual save only on clean exit
            # to avoid overwriting good data with an incomplete state.
            if self._loaded and exc_type is None and not self.auto_save:
                await self.save()
        finally:
            await self.close()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_path(self, key_path: str) -> list[str]:
        if not key_path or not isinstance(key_path, str):
            raise InvalidKeyPathError(key_path)
        segments = key_path.split(".")
        if any(not s for s in segments):
            raise EmptyPathSegmentError(key_path)
        return segments

    # ------------------------------------------------------------------
    # File I/O (caller must hold _lock)
    # ------------------------------------------------------------------

    async def _unsafe_load(self, default_copy: dict[str, Any]) -> None:
        """Load data from disk using the given default copy. Caller holds _lock."""
        if await aiofiles.os.path.exists(self.file_path):
            try:
                async with aiofiles.open(self.file_path, encoding="utf-8") as f:
                    content = await f.read()
                if content.strip():
                    loop = asyncio.get_running_loop()
                    loaded_data = await loop.run_in_executor(None, json5.loads, content)
                else:
                    loaded_data = default_copy

                if not isinstance(loaded_data, dict):
                    logger.warning("Root is not a dict, falling back to default")
                    self._data = default_copy
                else:
                    self._data = loaded_data
            except (ValueError, OSError) as e:
                logger.warning(f"Loading failed ({e}), falling back to default")
                self._data = default_copy
        else:
            self._data = default_copy
        self._loaded = True

    async def _do_load(self) -> None:
        """Background loading task. Called at most once. Respects closed flag."""
        # Prepare default copy asynchronously (outside _lock)
        default_copy = await self._get_fresh_default_copy()
        async with self._lock:
            # Abort if closed in the meantime
            if self._closed:
                return
            if not self._loaded:
                await self._cleanup_temp_file_async()
                await self._unsafe_load(default_copy)

    async def _ensure_loaded(self) -> None:
        """
        Ensure database is loaded. Starts a single background task if not already
        loading or loaded. All concurrent callers wait for the same task.
        Translates task cancellation (e.g. due to close()) into a RuntimeError.
        """
        if self._closed:
            raise DatabaseClosedError
        if self._loaded:
            return

        await self._start_load_task()
        await self._await_load_task()

        if self._closed:
            raise DatabaseClosedError
        if not self._loaded:
            raise LoadStateMismatchError

    async def _start_load_task(self) -> None:
        async with self._load_lock:
            if self._loaded:
                return
            if self._load_task is None or self._load_task.done():
                self._load_task = asyncio.create_task(self._do_load())

    async def _await_load_task(self) -> None:
        task = self._load_task
        if task is None:
            return
        try:
            await task
        except asyncio.CancelledError:
            if self._closed:
                raise DatabaseClosedError from None
            raise LoadTaskCancelledError from None
        except Exception:
            async with self._load_lock:
                if self._load_task and self._load_task.done():
                    self._load_task = None
            raise

    async def load(self) -> None:
        """Explicitly load database. Same as _ensure_loaded()."""
        await self._ensure_loaded()

    async def reload(
        self, callback: Callable[[], Awaitable[Any]] | None = None
    ) -> None:
        """
        Force reload from disk, then optionally await *callback*.
        The callback is awaited **after** the lock is released.

        Does NOT cancel existing load tasks - it waits for them to complete
        before reloading. This avoids leaking CancelledError to other waiters.
        """
        if self._closed:
            raise DatabaseClosedError

        if callback is not None and not asyncio.iscoroutinefunction(callback):
            raise CallbackTypeError

        # Prepare a fresh default copy before acquiring locks
        default_copy = await self._get_fresh_default_copy()

        # Wait for any ongoing load task to settle (no cancel)
        if self._load_task and not self._load_task.done():
            result = await asyncio.gather(self._load_task, return_exceptions=True)
            load_result = result[0]
            if isinstance(load_result, asyncio.CancelledError):
                if self._closed:
                    raise DatabaseClosedError from None
                raise LoadTaskCancelledError from None

        # Serialise reload with other loading attempts
        async with self._load_lock, self._lock:
            self._loaded = False
            # Cancel any stale load task (should already be done, but be safe)
            if self._load_task and not self._load_task.done():
                self._load_task.cancel()
            self._load_task = None
            await self._cleanup_temp_file_async()
            await self._unsafe_load(default_copy)
        if callback is not None:
            await callback()

    async def _unsafe_save_data(self, data: dict[str, Any]) -> None:
        """
        Serialize *data* and atomically write it to disk.
        Does NOT modify ``self._data``.  Caller must hold ``self._lock``.
        """
        await aiofiles.os.makedirs(self.file_path.parent, exist_ok=True)

        def _serialize():
            return json5.dumps(data, indent=self.indent, ensure_ascii=self.ensure_ascii)

        loop = asyncio.get_running_loop()
        try:
            content = await loop.run_in_executor(None, _serialize)
        except TypeError as e:
            msg = (
                "Serialization failure: data contains "
                f"non-JSON5-serializable objects: {e}"
            )
            logger.exception(msg)
            raise RuntimeError(msg) from e

        # Write to temp file
        async with aiofiles.open(self.temp_file_path, "w", encoding="utf-8") as f:
            await f.write(content)

        # Atomically replace the main file
        try:
            await aiofiles.os.replace(self.temp_file_path, self.file_path)
        except OSError as exc:
            logger.exception(
                "Atomic replace failed. Original file is unchanged. "
                f"Temporary file may remain at {self.temp_file_path}"
            )
            # Best-effort cleanup of lingering temp file
            await self._cleanup_temp_file_async()
            raise AtomicReplacementError from exc

        # Update watch mtime to avoid false reload triggers
        try:
            stat_result = await aiofiles.os.stat(self.file_path)
            self._watch_mtime = stat_result.st_mtime
        except FileNotFoundError:
            self._watch_mtime = 0.0

    async def _unsafe_save(self) -> None:
        """Save the current ``self._data`` to disk atomically."""
        await self._unsafe_save_data(self._data)

    async def save(self) -> None:
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            await self._unsafe_save()

    # ------------------------------------------------------------------
    # CRUD (auto_save=True guarantees strict atomicity: disk first, then memory)
    # ------------------------------------------------------------------

    async def read(
        self,
        key_path: str | None = None,
        default: Any = None,
        *,
        use_deepcopy: bool = True,
    ) -> Any:
        """
        Read data at *key_path*. Automatically loads database if not yet loaded.

        If ``use_deepcopy`` is True and the value is a dict or list, the method:
          1. Under the lock, obtains a reference to the value.
          2. If the value is a container, performs a **shallow copy** (dict/list copy)
             while still holding the lock.
          3. Releases the lock.
          4. Deep copies the shallow copy in a thread pool and returns it.

        Returns a possibly **non-atomic snapshot** (see class docstring). For strong
        consistency, use ``atomic_read()``.
        """
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError

        async with self._lock:
            if key_path is None:
                val = self._data
            else:
                segments = self._validate_path(key_path)
                parent, key, exists = self._navigate_to_parent(
                    segments, create_missing=False
                )
                if not exists:
                    return default
                val = parent[key]

            if not use_deepcopy or not isinstance(val, (dict, list)):
                return val

            # Shallow copy under lock to protect container structure
            if isinstance(val, dict):
                shallow = dict(val)
            elif isinstance(val, list):
                shallow = list(val)
            else:
                shallow = val  # pragma: no cover

        # Deepcopy outside lock in thread pool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, deepcopy, shallow)

    async def atomic_read(
        self, key_path: str | None = None, default: Any = None
    ) -> Any:
        """
        Read data at *key_path* and return an **atomic snapshot** (strong consistency).
        This method performs a deep copy **inside the lock** and thus may briefly
        block the event loop for large data structures. Use only when you cannot
        tolerate the weak consistency of ``read(use_deepcopy=True)``.
        """
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError

        async with self._lock:
            if key_path is None:
                val = self._data
            else:
                segments = self._validate_path(key_path)
                parent, key, exists = self._navigate_to_parent(
                    segments, create_missing=False
                )
                if not exists:
                    return default
                val = parent[key]
            # Synchronous deepcopy (may block event loop)
            return deepcopy(val) if isinstance(val, (dict, list)) else val

    async def set(self, key_path: str, value: Any) -> None:
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        await self._set_with_condition(key_path, value, mode="upsert")

    async def create(self, key_path: str, value: Any) -> bool:
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        return await self._set_with_condition(key_path, value, mode="create")

    async def update(self, key_path: str, value: Any) -> bool:
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        return await self._set_with_condition(key_path, value, mode="update")

    async def _set_with_condition(self, key_path: str, value: Any, mode: str) -> bool:
        async with self._lock:
            if self.auto_save:
                # Atomic path: operate on a deep copy, persist it, then swap
                loop = asyncio.get_running_loop()
                data_copy: dict[str, Any] = await loop.run_in_executor(
                    None, deepcopy, self._data
                )

                segments = self._validate_path(key_path)
                create_missing = mode != "update"
                parent, key, exists = self._navigate_to_parent(
                    segments, create_missing=create_missing, root=data_copy
                )

                if mode == "create" and exists:
                    return False
                if mode == "update" and (parent is None or not exists):
                    return False

                parent[key] = value

                # Try to persist the new state; only replace memory on success
                await self._unsafe_save_data(data_copy)
                self._data = data_copy
                return True
            # Non-auto-save: modify in-memory directly, no disk write.
            segments = self._validate_path(key_path)
            create_missing = mode != "update"
            parent, key, exists = self._navigate_to_parent(
                segments, create_missing=create_missing
            )

            if mode == "create" and exists:
                return False
            if mode == "update" and (parent is None or not exists):
                return False

            parent[key] = value
            return True

    async def set_batch(self, updates: dict[str, Any]) -> None:
        """
        Atomically apply a batch of updates.  If ``auto_save`` is True the new state
        is persisted *before* the in-memory data is replaced; no partial modifications
        are ever visible to readers or persisted on failure.

        Updates within a batch are applied independently; do not rely on insertion
        order to achieve cascading changes (e.g., setting a key and then a sub-key).
        The method operates on a deep copy of the database, applies every entry in
        the order they are iterated, and then commits the full result atomically.
        """
        if not updates:
            return
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError

        async with self._lock:
            loop = asyncio.get_running_loop()
            data_copy: dict[str, Any] = await loop.run_in_executor(
                None, deepcopy, self._data
            )

            for path, val in updates.items():
                segments = self._validate_path(path)
                parent, key, _ = self._navigate_to_parent(
                    segments, create_missing=True, root=data_copy
                )
                parent[key] = val

            if self.auto_save:
                # Persist the new state first; only update memory on success
                await self._unsafe_save_data(data_copy)
            self._data = data_copy

    async def delete(self, key_path: str) -> bool:
        """
        Delete the value at *key_path*.  Returns True if the key existed.

        Deleting an element from a list (when *key_path* ends with a numeric index)
        will remove that element and shift all following items, which changes the
        meaning of subsequent index-based accesses.
        """
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            if self.auto_save:
                loop = asyncio.get_running_loop()
                data_copy: dict[str, Any] = await loop.run_in_executor(
                    None, deepcopy, self._data
                )

                segments = self._validate_path(key_path)
                parent, key, exists = self._navigate_to_parent(
                    segments, create_missing=False, root=data_copy
                )
                if not exists:
                    return False

                del parent[key]
                await self._unsafe_save_data(data_copy)
                self._data = data_copy
                return True
            segments = self._validate_path(key_path)
            parent, key, exists = self._navigate_to_parent(
                segments, create_missing=False
            )
            if not exists:
                return False
            del parent[key]
            return True

    async def exists(self, key_path: str) -> bool:
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            segments = self._validate_path(key_path)
            _, _, exists = self._navigate_to_parent(segments, create_missing=False)
            return exists

    async def clear(self) -> None:
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            if self.auto_save:
                # Persist an empty dict atomically
                empty: dict[str, Any] = {}
                await self._unsafe_save_data(empty)
                self._data = empty
            else:
                self._data = {}

    # ------------------------------------------------------------------
    # Internal navigation
    # ------------------------------------------------------------------

    def _navigate_to_parent(
        self,
        segments: list[str],
        *,
        create_missing: bool,
        root: dict[str, Any] | None = None,
    ) -> tuple[Any, Any, bool]:
        """
        Navigate segments and return (parent_container, key/index, exists).
        If ``root`` is given, navigation starts there; otherwise ``self._data`` is used.

        Only non-negative integer segments are treated as list indices; negative numbers
        are handled as dictionary keys.
        """
        *parents, target_key = segments
        path = ".".join(segments)
        current: Any = root if root is not None else self._data
        traversed = self._traverse_parents(
            current,
            parents,
            create_missing=create_missing,
            path=path,
        )
        if traversed is None:
            return None, None, False
        return self._resolve_target(
            traversed,
            target_key,
            create_missing=create_missing,
            path=path,
        )

    def _traverse_parents(
        self,
        current: Any,
        parents: list[str],
        *,
        create_missing: bool,
        path: str,
    ) -> Any | None:
        for segment in parents:
            if isinstance(current, dict):
                if segment not in current:
                    if not create_missing:
                        return None
                    current[segment] = {}
                current = current[segment]
                continue

            if isinstance(current, list) and segment.isdigit():
                current = self._descend_list(
                    current,
                    int(segment),
                    create_missing=create_missing,
                    path=path,
                )
                if current is None:
                    return None
                continue

            if create_missing:
                actual_type = type(current).__name__
                raise ParentPathResolutionError(segment, actual_type, path)
            return None

        return current

    def _descend_list(
        self,
        current: list[Any],
        index: int,
        *,
        create_missing: bool,
        path: str,
    ) -> Any | None:
        if index >= len(current):
            if not create_missing:
                return None
            current.extend([None] * (index - len(current) + 1))
        if current[index] is None and create_missing:
            raise IntermediateListNoneError(index, path)
        return current[index]

    def _resolve_target(
        self,
        current: Any,
        target_key: str,
        *,
        create_missing: bool,
        path: str,
    ) -> tuple[Any, Any, bool]:
        if isinstance(current, dict):
            return current, target_key, target_key in current

        if isinstance(current, list) and target_key.isdigit():
            idx = int(target_key)
            if idx >= len(current):
                if not create_missing:
                    return None, None, False
                current.extend([None] * (idx - len(current) + 1))
                return current, idx, False
            return current, idx, True

        if create_missing:
            actual_type = type(current).__name__
            raise TerminalPathResolutionError(actual_type, target_key, path)
        return None, None, False

    # ------------------------------------------------------------------
    # File change watcher
    # ------------------------------------------------------------------

    async def watch(
        self,
        callback: Callable[[], Awaitable[Any]] | None = None,
        interval: float = 1.0,
    ) -> None:
        """
        Start polling the underlying file for external modifications.
        When a change is detected the database is automatically reloaded and
        *callback* (if provided) is awaited.

        Only one watcher can be active at a time. Call ``close()`` to stop it.

        **Race condition warning**: Concurrent writes performed by your application
        while the watcher is active may be overwritten by an external change, or
        your writes may overwrite external changes.  Coordinate carefully when
        using the watcher alongside writers.

        If a reload (or the callback) fails, the error is logged and the watcher
        continues running; the database will attempt to reload again on the next
        detected change. External notification of such failures is not provided
        by default - wrap the callback if you need custom error handling.
        """
        if callback is not None and not asyncio.iscoroutinefunction(callback):
            raise CallbackTypeError

        if self._watch_task is not None and not self._watch_task.done():
            raise WatchAlreadyRunningError

        self._watch_task = asyncio.create_task(self._watch_loop(callback, interval))

    async def _watch_loop(
        self,
        callback: Callable[[], Awaitable[Any]] | None,
        interval: float,
    ) -> None:
        await self._ensure_loaded()
        try:
            stat_result = await aiofiles.os.stat(self.file_path)
            self._watch_mtime = stat_result.st_mtime
        except FileNotFoundError:
            self._watch_mtime = 0.0
        except OSError:
            logger.exception("Initial watch stat failed")
            self._watch_mtime = 0.0

        while True:
            await asyncio.sleep(interval)
            if self._closed:
                break
            try:
                stat_result = await aiofiles.os.stat(self.file_path)
                current_mtime = stat_result.st_mtime
            except FileNotFoundError:
                current_mtime = 0.0
            except OSError:
                logger.exception("Watch stat failed")
                continue

            if current_mtime != self._watch_mtime:
                self._watch_mtime = current_mtime
                logger.info("File change detected, reloading")
                try:
                    await self.reload(callback)
                except Exception:
                    logger.exception("Reload/callback failed in watcher")
