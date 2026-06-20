"""JSON5 数据库同步辅助函数。

提供同步读取和确保 JSON5 字典文件存在的工具函数。

Synchronous helper functions for the JSON5 database module.
"""

from __future__ import annotations

import contextlib
from copy import deepcopy
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import json5

from .exceptions import InvalidJSON5RootTypeError, JSON5FileReadError


def load_json5_dict_sync(
    file_path: str | Path,
    *,
    default: dict[str, Any] | None = None,
    merge_default: bool = False,
) -> dict[str, Any]:
    """同步读取 JSON5 字典文件。

    该 helper 面向插件导入期等不能 await 的轻量配置场景。文件不存在或
    内容为空时返回 default 的深拷贝；文件存在但解析失败时抛出明确错误。
    """
    path = Path(file_path)
    default_copy: dict[str, Any] = deepcopy(default) if default is not None else {}
    if not path.exists():
        return default_copy

    try:
        content = path.read_text(encoding="utf-8")
        loaded = json5.loads(content) if content.strip() else default_copy
    except (OSError, ValueError) as exc:
        raise JSON5FileReadError(path, exc) from exc

    if not isinstance(loaded, dict):
        raise InvalidJSON5RootTypeError(path, type(loaded))

    if not merge_default:
        return loaded
    return default_copy | loaded


def ensure_json5_dict_file_sync(
    file_path: str | Path,
    default: dict[str, Any],
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """确保 JSON5 字典文件存在，已存在时不覆盖。"""
    path = Path(file_path)
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp.json5")
    try:
        content = json5.dumps(
            default,
            indent=indent,
            ensure_ascii=ensure_ascii,
        )
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
    except (OSError, TypeError, ValueError) as exc:
        with contextlib.suppress(OSError):
            temp_path.unlink()
        raise JSON5FileReadError(path, exc) from exc
    return path


async def ensure_json5_dict_file_async(
    file_path: str | Path,
    default: dict[str, Any],
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """异步确保 JSON5 字典文件存在，已存在时不覆盖。

    镜像 ``ensure_json5_dict_file_sync`` 的逻辑，但使用 ``aiofiles`` 进行
    非阻塞 I/O，适合在事件循环中调用（如 ``startup()``）。
    """
    path = Path(file_path)
    if await aiofiles.os.path.exists(path):
        return path

    await aiofiles.os.makedirs(path.parent, exist_ok=True)
    temp_path = path.with_suffix(".tmp.json5")
    try:
        content = json5.dumps(
            default,
            indent=indent,
            ensure_ascii=ensure_ascii,
        )
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        await aiofiles.os.replace(temp_path, path)
    except (OSError, TypeError, ValueError) as exc:
        with contextlib.suppress(OSError):
            await aiofiles.os.unlink(temp_path)
        raise JSON5FileReadError(path, exc) from exc
    return path


async def write_json5_dict_file_async(
    file_path: str | Path,
    data: dict[str, Any],
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """异步原子写入 JSON5 字典文件，覆盖已有内容。

    与 ``ensure_json5_dict_file_async`` 不同，该函数始终写入数据，
    适合持久化需要覆盖旧内容的场景（如状态保存）。
    """
    path = Path(file_path)
    await aiofiles.os.makedirs(path.parent, exist_ok=True)
    temp_path = path.with_suffix(".tmp.json5")
    try:
        content = json5.dumps(
            data,
            indent=indent,
            ensure_ascii=ensure_ascii,
        )
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        await aiofiles.os.replace(temp_path, path)
    except (OSError, TypeError, ValueError) as exc:
        with contextlib.suppress(OSError):
            await aiofiles.os.unlink(temp_path)
        raise JSON5FileReadError(path, exc) from exc
    return path
