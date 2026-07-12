"""Async serialization helpers for the TOML store."""

from __future__ import annotations

import asyncio
from copy import deepcopy
import logging
from typing import Any

import rtoml

from .exceptions import TOMLSerializationError

logger = logging.getLogger(__name__)


async def _deepcopy_async[T](value: T) -> T:
    return await asyncio.to_thread(deepcopy, value)


def _normalize_toml_value(value: Any, *, in_list: bool = False) -> Any:
    if value is None:
        if in_list:
            raise TOMLSerializationError("None inside a list is not supported")
        return None
    if isinstance(value, dict):
        return {
            str(key): normalized
            for key, item in value.items()
            if (normalized := _normalize_toml_value(item)) is not None
        }
    if isinstance(value, list):
        return [_normalize_toml_value(item, in_list=True) for item in value]
    return value


def _toml_dumps(data: dict[str, Any], *, schema_basename: str | None = None) -> str:
    normalized = _normalize_toml_value(data)
    try:
        content = rtoml.dumps(normalized, pretty=True, none_value=None)
    except (TypeError, ValueError) as exc:
        raise TOMLSerializationError(str(exc)) from exc
    if schema_basename is None:
        return content
    return f"#:schema ./{schema_basename}\n{content}"


async def _toml_loads_async(content: str) -> dict[str, Any]:
    return await asyncio.to_thread(rtoml.loads, content)


async def _toml_dumps_async(
    data: dict[str, Any], *, schema_basename: str | None = None
) -> str:
    return await asyncio.to_thread(
        _toml_dumps,
        data,
        schema_basename=schema_basename,
    )
