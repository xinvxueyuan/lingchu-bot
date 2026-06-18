"""JSON5 数据库异步辅助函数。

提供深拷贝、JSON5 加载和序列化的异步封装，以及模块日志记录器。

Async helper functions for the JSON5 database module.
"""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import Any, cast

import json5

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
