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

from ._async_db import RobustAsyncJSON5DB
from ._sync import (
    ensure_json5_dict_file_async,
    ensure_json5_dict_file_sync,
    load_json5_dict_sync,
    write_json5_dict_file_async,
)
from .exceptions import (
    AtomicReplacementError,
    CallbackTypeError,
    DatabaseClosedError,
    DatabaseError,
    EmptyPathSegmentError,
    IntermediateListNoneError,
    InvalidDefaultTypeError,
    InvalidJSON5RootTypeError,
    InvalidKeyPathError,
    JSON5FileReadError,
    LoadStateMismatchError,
    LoadTaskCancelledError,
    ParentPathResolutionError,
    TerminalPathResolutionError,
    WatchAlreadyRunningError,
)

__all__ = [
    "AtomicReplacementError",
    "CallbackTypeError",
    "DatabaseClosedError",
    "DatabaseError",
    "EmptyPathSegmentError",
    "IntermediateListNoneError",
    "InvalidDefaultTypeError",
    "InvalidJSON5RootTypeError",
    "InvalidKeyPathError",
    "JSON5FileReadError",
    "LoadStateMismatchError",
    "LoadTaskCancelledError",
    "ParentPathResolutionError",
    "RobustAsyncJSON5DB",
    "TerminalPathResolutionError",
    "WatchAlreadyRunningError",
    "ensure_json5_dict_file_async",
    "ensure_json5_dict_file_sync",
    "load_json5_dict_sync",
    "write_json5_dict_file_async",
]
