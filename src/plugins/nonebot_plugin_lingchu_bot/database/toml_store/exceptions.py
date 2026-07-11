"""TOML 数据库异常定义。

提供 TOML 数据库模块使用的所有异常类。

Exception classes for the TOML database module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class DatabaseError(Exception):
    """TOML 数据库错误的基础异常。

    用于表示该模块中的通用存储错误，不承载业务语义。

    Base exception for TOML database errors.
    This represents generic storage failures in this module and does not
    encode application-specific semantics.
    """


class InvalidDefaultTypeError(TypeError, DatabaseError):
    """默认值类型不合法时抛出。

    The provided default value has an invalid type.
    """

    def __init__(self, actual_type: type[Any]) -> None:
        super().__init__(f"default must be a dict, got {actual_type}")


class InvalidTOMLRootTypeError(TypeError, DatabaseError):
    """TOML 文件根对象不是字典时抛出。"""

    def __init__(self, file_path: Path, actual_type: type[Any]) -> None:
        super().__init__(
            f"TOML root in {file_path} must be a dict, got {actual_type.__name__}"
        )


class TOMLFileReadError(RuntimeError, DatabaseError):
    """TOML 文件读取或解析失败时抛出。"""

    def __init__(self, file_path: Path, reason: BaseException) -> None:
        super().__init__(f"Failed to read TOML file {file_path}: {reason}")


class TOMLSerializationError(TypeError, DatabaseError):
    """A value cannot be represented without changing its TOML semantics."""


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
