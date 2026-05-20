"""异步 JSON5 数据库客户端。

提供基于 JSON5 文件的异步数据存取、原子写入、嵌套键路径访问和文件监听。
支持 dict/list 路径导航、可选自动保存以及显式关闭；仅适合存放 JSON5 兼容
对象，包括 dict、list、str、int、float、bool 和 None。

Asynchronous JSON5 database client.

This module provides asynchronous JSON5-backed storage with atomic writes,
nested-key navigation, optional file watching, and explicit close semantics.
It supports dict/list path navigation, optional auto-save, and only stores
JSON5-compatible objects: dict, list, str, int, float, bool, and None.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, cast

import aiofiles
import aiofiles.os
import json5

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from types import TracebackType

logger = logging.getLogger(__name__)


async def _deepcopy_async[T](value: T) -> T:
    return cast("T", await asyncio.to_thread(deepcopy, value))


async def _json5_loads_async(content: str) -> Any:
    return await asyncio.to_thread(json5.loads, content)


async def _json5_dumps_async(
    data: dict[str, Any], *, indent: int, ensure_ascii: bool
) -> str:
    return await asyncio.to_thread(
        json5.dumps,
        data,
        indent=indent,
        ensure_ascii=ensure_ascii,
    )


class DatabaseError(Exception):
    """JSON5 数据库错误的基础异常。

    用于表示该模块中的通用存储错误，不承载业务语义。

    Base exception for JSON5 database errors.
    This represents generic storage failures in this module and does not
    encode application-specific semantics.
    """


class InvalidDefaultTypeError(TypeError, DatabaseError):
    """默认值类型不合法时抛出。

    The provided default value has an invalid type.
    """

    def __init__(self, actual_type: type[Any]) -> None:
        super().__init__(f"default must be a dict, got {actual_type}")


class DatabaseClosedError(RuntimeError, DatabaseError):
    """数据库已关闭时抛出。

    Raised when an operation is attempted after close().
    """

    def __init__(self) -> None:
        super().__init__("Database is closed")


class InvalidKeyPathError(ValueError, DatabaseError):
    """键路径无效时抛出。

    Raised when the key path is empty or not a string.
    """

    def __init__(self, key_path: Any) -> None:
        super().__init__(f"Key path must be a non-empty string: {key_path!r}")


class EmptyPathSegmentError(ValueError, DatabaseError):
    """键路径包含空段时抛出。

    Raised when a dotted path contains an empty segment.
    """

    def __init__(self, key_path: str) -> None:
        super().__init__(
            f"Invalid key path: {key_path!r}, empty segments are not allowed"
        )


class LoadTaskCancelledError(RuntimeError, DatabaseError):
    """加载任务被意外取消时抛出。

    Raised when the background load task is cancelled unexpectedly.
    """

    def __init__(self) -> None:
        super().__init__("Load task was unexpectedly cancelled")


class LoadStateMismatchError(RuntimeError, DatabaseError):
    """加载状态不一致时抛出。

    Raised when loading finished but the database was not marked loaded.
    """

    def __init__(self) -> None:
        super().__init__("Loading completed but database not marked as loaded")


class CallbackTypeError(TypeError, DatabaseError):
    """回调类型不合法时抛出。

    Raised when a callback is not asynchronous or is otherwise invalid.
    """

    def __init__(self) -> None:
        super().__init__("callback must be an async function (or None)")


class AtomicReplacementError(RuntimeError, DatabaseError):
    """原子替换文件失败时抛出。

    Raised when the temporary file could not replace the target file.
    """

    def __init__(self) -> None:
        super().__init__("Atomic file replacement failed")


class WatchAlreadyRunningError(RuntimeError, DatabaseError):
    """文件监听已在运行时抛出。

    Raised when watch() is called while a watcher is already active.
    """

    def __init__(self) -> None:
        super().__init__("A watcher is already running")


class IntermediateListNoneError(ValueError, DatabaseError):
    """列表中间位置为 None 时抛出。

    Raised when navigation tries to descend through a None placeholder.
    """

    def __init__(self, index: int, path: str) -> None:
        super().__init__(
            f"Cannot create intermediate dictionary at list index {index} "
            f"(None placeholder). Provide explicit structure before "
            f"accessing through a non-numeric key. Path: {path}"
        )


class ParentPathResolutionError(ValueError, DatabaseError):
    """父路径无法继续下钻时抛出。

    Raised when a parent path segment cannot descend into the current node.
    """

    def __init__(self, segment: str, actual_type: str, path: str) -> None:
        super().__init__(
            f"Path resolution failed: parent at segment '{segment}' is "
            f"{actual_type}, cannot descend. Path: {path}"
        )


class TerminalPathResolutionError(ValueError, DatabaseError):
    """终端路径无法解析时抛出。

    Raised when the final container does not support the target key.
    """

    def __init__(self, actual_type: str, target_key: str, path: str) -> None:
        super().__init__(
            f"Terminal navigation failed: container type {actual_type} does "
            f"not support key '{target_key}'. Path: {path}"
        )


class RobustAsyncJSON5DB:
    """异步 JSON5 文件数据库。

    该类以 JSON5 文件为持久化后端，支持嵌套路径读写、原子保存、
    可选自动保存和文件变化监听。数据模型仅接受 JSON5 兼容对象；
    数值路径片段在非负时才会被解释为列表索引，删除列表索引会让
    后续元素左移。

    This class uses a JSON5 file as its persistence backend and supports nested
    path access, atomic saves, optional auto-save, and file-change watching.
    It only accepts JSON5-compatible objects. Numeric path segments are treated
    as list indices only when non-negative, and deleting a list index shifts
    subsequent items.
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
        """初始化数据库实例。

        Args:
            file_path: 数据文件路径 / Path to the data file.
            auto_save: 是否每次修改后自动落盘。
                Whether to persist changes immediately.
            indent: JSON5 输出缩进 / Indentation used for serialization.
            ensure_ascii: 是否转义非 ASCII 字符。
                Whether to escape non-ASCII characters.
            default: 默认数据模板 / Default data template.

        Raises:
            InvalidDefaultTypeError: default 不是字典时。
        """
        self.file_path = Path(file_path)
        self.temp_file_path = self.file_path.with_suffix(".tmp.json5")
        self.auto_save = auto_save
        self.indent = indent
        self.ensure_ascii = ensure_ascii

        if default is not None and not isinstance(default, dict):
            raise InvalidDefaultTypeError(type(default))
        self._raw_default: dict[str, Any] = (
            deepcopy(default) if default is not None else {}
        )

        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._loaded = False
        self._closed = False
        self._load_lock = asyncio.Lock()
        self._load_task: asyncio.Task | None = None
        self._watch_task: asyncio.Task | None = None
        self._watch_mtime: float = 0.0

    # ------------------------------------------------------------------
    # Properties & representation
    # ------------------------------------------------------------------

    @property
    def is_closed(self) -> bool:
        """判断数据库是否已关闭。

        Returns:
            已关闭返回 True / True if the database has been closed.
        """
        return self._closed

    def __repr__(self) -> str:
        """返回调试表示。

        Returns:
            便于调试的对象表示 / Debug-friendly object representation.
        """
        status = (
            "closed" if self._closed else ("loaded" if self._loaded else "not loaded")
        )
        return f"<RobustAsyncJSON5DB path={self.file_path!r} status={status}>"

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    async def _get_fresh_default_copy(self) -> dict[str, Any]:
        """获取新的默认模板副本。

        Returns:
            默认模板的深拷贝 / Deep copy of the default template.
        """
        return await _deepcopy_async(self._raw_default)

    async def _cleanup_temp_file_async(self) -> None:
        """异步清理临时文件。"""
        if await aiofiles.os.path.exists(self.temp_file_path):
            with contextlib.suppress(OSError):
                await aiofiles.os.remove(self.temp_file_path)

    async def close(self) -> None:
        """关闭数据库并清理后台任务。

        Stop watcher/load tasks, remove temporary files, and mark the database
        as closed.
        """
        if self._closed:
            return
        self._closed = True

        if self._load_task and not self._load_task.done():
            self._load_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._load_task

        if self._watch_task is not None and not self._watch_task.done():
            self._watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watch_task
        self._watch_task = None

        with contextlib.suppress(Exception):
            await self._cleanup_temp_file_async()

    async def __aenter__(self) -> Self:
        """进入异步上下文时自动加载数据库。"""
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
            if self._loaded and exc_type is None and not self.auto_save:
                await self.save()
        finally:
            await self.close()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_path(self, key_path: str) -> list[str]:
        """校验并拆分键路径。

        Args:
            key_path: 点分路径 / Dotted key path.

        Returns:
            路径段列表 / List of path segments.

        Raises:
            InvalidKeyPathError: 路径不是非空字符串时。
            EmptyPathSegmentError: 路径包含空段时。
        """
        if not key_path or not isinstance(key_path, str):
            raise InvalidKeyPathError(key_path)
        segments = key_path.split(".")
        if any(not s for s in segments):
            raise EmptyPathSegmentError(key_path)
        return segments

    async def _unsafe_load(self, default_copy: dict[str, Any]) -> None:
        """从磁盘加载数据。

        Args:
            default_copy: 读取失败时使用的默认副本 / Default copy used on load failure.

        Raises:
            无 / None.
        """
        if await aiofiles.os.path.exists(self.file_path):
            try:
                async with aiofiles.open(self.file_path, encoding="utf-8") as f:
                    content = await f.read()
                if content.strip():
                    loaded_data = await _json5_loads_async(content)
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
        """执行后台加载任务。"""
        default_copy = await self._get_fresh_default_copy()
        async with self._lock:
            if self._closed:
                return
            if not self._loaded:
                await self._cleanup_temp_file_async()
                await self._unsafe_load(default_copy)

    async def _ensure_loaded(self) -> None:
        """确保数据库已加载。

        启动时会复用同一个加载任务，多个并发调用者会等待同一任务完成。

        Ensure the database is loaded. Concurrent callers wait for the same load
        task, and cancellation caused by close() is mapped to a database error.
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
        """启动加载任务（若尚未存在）。"""
        async with self._load_lock:
            if self._loaded:
                return
            if self._load_task is None or self._load_task.done():
                self._load_task = asyncio.create_task(self._do_load())

    async def _await_load_task(self) -> None:
        """等待加载任务完成并转换取消异常。"""
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
        """显式加载数据库。

        Returns:
            None.
        """
        await self._ensure_loaded()

    async def reload(
        self, callback: Callable[[], Awaitable[Any]] | None = None
    ) -> None:
        """强制从磁盘重新加载。

        如果提供 callback，会在重新加载完成后、释放锁之后再等待回调。
        该方法不会取消已有加载任务，而是等待其完成后再继续。

        Force a reload from disk. If provided, callback is awaited after reload
        and after the lock is released. Existing load tasks are not cancelled;
        the method waits for them to finish first.
        """
        if self._closed:
            raise DatabaseClosedError

        if callback is not None and not asyncio.iscoroutinefunction(callback):
            raise CallbackTypeError

        default_copy = await self._get_fresh_default_copy()

        if self._load_task and not self._load_task.done():
            result = await asyncio.gather(self._load_task, return_exceptions=True)
            load_result = result[0]
            if isinstance(load_result, asyncio.CancelledError):
                if self._closed:
                    raise DatabaseClosedError from None
                raise LoadTaskCancelledError from None

        async with self._load_lock, self._lock:
            self._loaded = False
            if self._load_task and not self._load_task.done():
                self._load_task.cancel()
            self._load_task = None
            await self._cleanup_temp_file_async()
            await self._unsafe_load(default_copy)
        if callback is not None:
            await callback()

    async def _unsafe_save_data(self, data: dict[str, Any]) -> None:
        """序列化并原子写入数据。

        该方法不会直接修改 self._data；调用方需要持有锁。

        Serialize and atomically write data to disk. This does not modify
        self._data directly; the caller must hold the lock.
        """
        await aiofiles.os.makedirs(self.file_path.parent, exist_ok=True)

        try:
            content = await _json5_dumps_async(
                data, indent=self.indent, ensure_ascii=self.ensure_ascii
            )
        except TypeError as e:
            msg = (
                "Serialization failure: data contains "
                f"non-JSON5-serializable objects: {e}"
            )
            logger.exception(msg)
            raise RuntimeError(msg) from e

        async with aiofiles.open(self.temp_file_path, "w", encoding="utf-8") as f:
            await f.write(content)

        try:
            await aiofiles.os.replace(self.temp_file_path, self.file_path)
        except OSError as exc:
            logger.exception(
                "Atomic replace failed. Original file is unchanged. "
                f"Temporary file may remain at {self.temp_file_path}"
            )
            await self._cleanup_temp_file_async()
            raise AtomicReplacementError from exc

        try:
            stat_result = await aiofiles.os.stat(self.file_path)
            self._watch_mtime = stat_result.st_mtime
        except FileNotFoundError:
            self._watch_mtime = 0.0

    async def _unsafe_save(self) -> None:
        """将当前内存数据原子保存到磁盘。"""
        await self._unsafe_save_data(self._data)

    async def save(self) -> None:
        """保存当前数据。"""
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            await self._unsafe_save()

    async def read(
        self,
        key_path: str | None = None,
        default: Any = None,
        *,
        use_deepcopy: bool = True,
    ) -> Any:
        """读取指定路径的数据。

        若尚未加载，会自动触发加载。use_deepcopy=True 时会尽量返回安全快照。

        Read data at key_path. The database is loaded automatically if needed.
        When use_deepcopy is True and the value is a container, the method
        returns a defensive copy.
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

            if isinstance(val, dict):
                shallow = dict(val)
            elif isinstance(val, list):
                shallow = list(val)
            else:
                shallow = val

        return await _deepcopy_async(shallow)

    async def atomic_read(
        self, key_path: str | None = None, default: Any = None
    ) -> Any:
        """原子读取指定路径的数据。

        This returns a strong-consistency snapshot by deep-copying under the lock.
        Large snapshots are copied in a worker thread so the event loop stays
        responsive while writers remain serialized by the database lock.
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
            return await _deepcopy_async(val) if isinstance(val, (dict, list)) else val

    async def set(self, key_path: str, value: Any) -> None:
        """设置或覆盖指定路径的值。"""
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        await self._set_with_condition(key_path, value, mode="upsert")

    async def create(self, key_path: str, value: Any) -> bool:
        """仅在路径不存在时创建值。"""
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        return await self._set_with_condition(key_path, value, mode="create")

    async def update(self, key_path: str, value: Any) -> bool:
        """仅在路径存在时更新值。"""
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        return await self._set_with_condition(key_path, value, mode="update")

    async def _set_with_condition(self, key_path: str, value: Any, mode: str) -> bool:
        """按模式写入单个路径。"""
        async with self._lock:
            if self.auto_save:
                data_copy = await _deepcopy_async(self._data)

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

                await self._unsafe_save_data(data_copy)
                self._data = data_copy
                return True
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
        """批量应用更新。

        The batch is applied to a deep copy first and then committed atomically.
        Updates are independent; do not rely on ordering for cascading changes.
        """
        if not updates:
            return
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError

        async with self._lock:
            data_copy = await _deepcopy_async(self._data)

            for path, val in updates.items():
                segments = self._validate_path(path)
                parent, key, _ = self._navigate_to_parent(
                    segments, create_missing=True, root=data_copy
                )
                parent[key] = val

            if self.auto_save:
                await self._unsafe_save_data(data_copy)
            self._data = data_copy

    async def delete(self, key_path: str) -> bool:
        """删除指定路径的值。

        Returns True if the key existed. Deleting a list item shifts later items.
        """
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            if self.auto_save:
                data_copy = await _deepcopy_async(self._data)

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
        """判断指定路径是否存在。"""
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            segments = self._validate_path(key_path)
            _, _, exists = self._navigate_to_parent(segments, create_missing=False)
            return exists

    async def clear(self) -> None:
        """清空所有数据。"""
        await self._ensure_loaded()
        if self._closed:
            raise DatabaseClosedError
        async with self._lock:
            if self.auto_save:
                empty: dict[str, Any] = {}
                await self._unsafe_save_data(empty)
                self._data = empty
            else:
                self._data = {}

    def _navigate_to_parent(
        self,
        segments: list[str],
        *,
        create_missing: bool,
        root: dict[str, Any] | None = None,
    ) -> tuple[Any, Any, bool]:
        """导航到父容器并返回目标键。

        If root is provided, navigation starts there; otherwise self._data is
        used. Only non-negative integer segments are treated as list indices.
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
        """逐级遍历父路径。"""
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
        """下钻到列表元素。"""
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
        """解析最终目标键或索引。"""
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

    async def watch(
        self,
        callback: Callable[[], Awaitable[Any]] | None = None,
        interval: float = 1.0,
    ) -> None:
        """开始监听文件外部修改。

        Only one watcher can run at a time. If a change is detected, the
        database reloads automatically and the optional callback is awaited.
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
        """监听循环。"""
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
