"""TOML 存储异常定义。

提供 TOML 存储助手模块使用的异常类。

Exception classes for the TOML storage helpers.
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
