"""异步 TOML 数据库客户端。

提供基于 TOML 文件的异步数据存取、原子写入、嵌套键路径访问和文件监听。
支持 dict/list 路径导航、可选自动保存以及显式关闭；仅适合存放 TOML 兼容
对象。字典中的 None 表示缺少键，列表中的 None 不受支持。

Asynchronous TOML database client.

This module provides asynchronous TOML-backed storage with atomic writes,
nested-key navigation, optional file watching, and explicit close semantics.
It supports dict/list path navigation, optional auto-save, and only stores
TOML-compatible objects. None omits a mapping key and is invalid in lists.
"""

from __future__ import annotations

from ._async_db import RobustAsyncTOMLDB
from ._sync import (
    ensure_toml_dict_file_async,
    ensure_toml_dict_file_sync,
    load_toml_dict_async,
    load_toml_dict_sync,
    write_toml_dict_file_async,
)
from .exceptions import (
    AtomicReplacementError,
    CallbackTypeError,
    DatabaseClosedError,
    DatabaseError,
    EmptyPathSegmentError,
    IntermediateListNoneError,
    InvalidDefaultTypeError,
    InvalidKeyPathError,
    InvalidTOMLRootTypeError,
    LoadStateMismatchError,
    LoadTaskCancelledError,
    ParentPathResolutionError,
    TerminalPathResolutionError,
    TOMLFileReadError,
    TOMLSerializationError,
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
    "InvalidKeyPathError",
    "InvalidTOMLRootTypeError",
    "LoadStateMismatchError",
    "LoadTaskCancelledError",
    "ParentPathResolutionError",
    "RobustAsyncTOMLDB",
    "TOMLFileReadError",
    "TOMLSerializationError",
    "TerminalPathResolutionError",
    "WatchAlreadyRunningError",
    "ensure_toml_dict_file_async",
    "ensure_toml_dict_file_sync",
    "load_toml_dict_async",
    "load_toml_dict_sync",
    "write_toml_dict_file_async",
]
