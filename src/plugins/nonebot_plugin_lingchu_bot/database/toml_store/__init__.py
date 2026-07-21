"""异步 TOML 存储助手。

提供基于 TOML 文件的异步数据存取、原子写入和 schema 引用注入。
仅适合存放 TOML 兼容对象。

Asynchronous TOML storage helpers.

This module provides asynchronous TOML-backed storage with atomic writes
and schema reference injection. It only accepts TOML-compatible objects.
"""

from __future__ import annotations

from ._sync import (
    ensure_toml_dict_file_async,
    ensure_toml_dict_file_sync,
    load_toml_dict_async,
    load_toml_dict_sync,
    write_toml_dict_file_async,
)
from .exceptions import (
    DatabaseError,
    InvalidDefaultTypeError,
    InvalidTOMLRootTypeError,
    TOMLFileReadError,
    TOMLSerializationError,
)

__all__ = [
    "DatabaseError",
    "InvalidDefaultTypeError",
    "InvalidTOMLRootTypeError",
    "TOMLFileReadError",
    "TOMLSerializationError",
    "ensure_toml_dict_file_async",
    "ensure_toml_dict_file_sync",
    "load_toml_dict_async",
    "load_toml_dict_sync",
    "write_toml_dict_file_async",
]
