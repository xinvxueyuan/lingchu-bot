"""TOML 配置文件的简单异步 CRUD 工具。"""

from __future__ import annotations

import asyncio
import tomllib
from typing import TYPE_CHECKING, Any

from nonebot import require
from nonebot.log import logger

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, MutableMapping
    from pathlib import Path

import tomli_w

DEFAULT_CONFIG_FILE = "lc-bot.toml"


def _get_config_file(file_name: str | Path = DEFAULT_CONFIG_FILE) -> Path:
    path = store.get_plugin_config_file(str(file_name))
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(f"配置文件路径: {path}")
    return path


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        logger.warning(f"配置文件不存在: {path}")
        return {}
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as e:
        logger.error(f"读取配置文件失败: {path}, 错误: {e}")
        return {}
    else:
        logger.info(f"读取配置文件成功: {path}")
        return data


def _dump_toml(path: Path, data: Mapping[str, Any]) -> None:
    try:
        with path.open("wb") as file:
            tomli_w.dump(dict(data), file)
        logger.info(f"写入配置文件成功: {path}")
    except Exception as e:
        logger.error(f"写入配置文件失败: {path}, 错误: {e}")
        raise


async def read_config(
    file_name: str | Path = DEFAULT_CONFIG_FILE,
) -> tuple[dict[str, Any], bool]:
    """
    读取配置文件，若文件不存在则返回 (空字典, False)。
    参数：
        file_name: 配置文件名或路径
    返回：
        (配置字典, 状态)
        状态为 True 表示读取成功，False 表示失败或文件不存在。
    """
    path = _get_config_file(file_name)
    logger.debug(f"开始异步读取配置: {path}")
    try:
        data = await asyncio.to_thread(_load_toml, path)
    except (OSError, tomllib.TOMLDecodeError) as e:
        logger.error(f"异步读取配置失败: {path}, 错误: {e}")
        return {}, False
    else:
        success = bool(data)
        return data, success


async def write_config(
    data: Mapping[str, Any], file_name: str | Path = DEFAULT_CONFIG_FILE
) -> tuple[Path | None, bool]:
    """
    覆盖写入配置文件。
    参数：
        data: 要写入的配置字典
        file_name: 配置文件名或路径
    返回：
        (文件路径, 状态)
        状态为 True 表示写入成功，False 表示失败。
    """
    path = _get_config_file(file_name)
    logger.debug(f"开始异步写入配置: {path}")
    try:
        await asyncio.to_thread(_dump_toml, path, data)
    except (OSError, TypeError) as e:
        logger.error(f"异步写入配置失败: {path}, 错误: {e}")
        return None, False
    else:
        return path, True


async def update_config(
    updates: Mapping[str, Any], file_name: str | Path = DEFAULT_CONFIG_FILE
) -> tuple[dict[str, Any], bool]:
    """
    更新配置（浅合并），返回 (最新配置, 状态)。
    参数：
        updates: 要更新的键值对
        file_name: 配置文件名或路径
    返回：
        (最新配置字典, 状态)
        状态为 True 表示更新成功，False 表示失败。
    """
    logger.debug(f"更新配置: {updates}")
    current, _ = await read_config(file_name)
    merged: MutableMapping[str, Any] = {**current, **updates}
    _, success = await write_config(merged, file_name)
    logger.info(f"配置已更新: {file_name}")
    return dict(merged), success


async def delete_keys(
    keys: Iterable[str], file_name: str | Path = DEFAULT_CONFIG_FILE
) -> tuple[dict[str, Any], bool]:
    """
    删除指定键，返回 (最新配置, 状态)。
    参数：
        keys: 要删除的键列表
        file_name: 配置文件名或路径
    返回：
        (最新配置字典, 状态)
        状态为 True 表示删除并写入成功，False 表示失败。
    """
    logger.debug(f"删除配置键: {list(keys)}")
    current, _ = await read_config(file_name)
    for key in keys:
        current.pop(key, None)
    _, success = await write_config(current, file_name)
    logger.info(f"配置键已删除: {list(keys)}")
    return current, success


async def get_value(
    key: str,
    *,
    default: Any | None = None,
    file_name: str | Path = DEFAULT_CONFIG_FILE,
) -> tuple[Any, bool]:
    """
    获取单个配置值。
    参数：
        key: 配置键
        default: 默认值
        file_name: 配置文件名或路径
    返回：
        (值, 状态)
        状态为 True 表示获取成功，False 表示失败或无此键。
    """
    logger.debug(f"获取配置键: {key}")
    config, success = await read_config(file_name)
    value = config.get(key, default)
    logger.info(f"获取配置键: {key}，值: {value}")
    return value, success and (key in config)


async def set_value(
    key: str, value: Any, file_name: str | Path = DEFAULT_CONFIG_FILE
) -> tuple[dict[str, Any], bool]:
    """
    设置单个键值，返回 (最新配置, 状态)。
    参数：
        key: 配置键
        value: 配置值
        file_name: 配置文件名或路径
    返回：
        (最新配置字典, 状态)
        状态为 True 表示设置成功，False 表示失败。
    """
    logger.debug(f"设置配置键: {key}，值: {value}")
    result, success = await update_config({key: value}, file_name)
    logger.info(f"配置键已设置: {key}，值: {value}")
    return result, success


# 批量设置键值
async def bulk_set(
    items: Mapping[str, Any], file_name: str | Path = DEFAULT_CONFIG_FILE
) -> tuple[dict[str, Any], bool]:
    """
    批量设置多个键值，返回 (最新配置, 状态)。
    参数：
        items: 要设置的键值对
        file_name: 配置文件名或路径
    返回：
        (最新配置字典, 状态)
        状态为 True 表示设置成功，False 表示失败。
    """
    logger.debug(f"批量设置配置: {items}")
    result, success = await update_config(items, file_name)
    logger.info(f"批量配置已设置: {list(items.keys())}")
    return result, success


# 批量删除键
async def bulk_delete(
    keys: Iterable[str], file_name: str | Path = DEFAULT_CONFIG_FILE
) -> tuple[dict[str, Any], bool]:
    """
    批量删除多个键，返回 (最新配置, 状态)。
    参数：
        keys: 要删除的键列表
        file_name: 配置文件名或路径
    返回：
        (最新配置字典, 状态)
        状态为 True 表示删除并写入成功，False 表示失败。
    """
    logger.debug(f"批量删除配置键: {list(keys)}")
    current, _ = await read_config(file_name)
    for key in keys:
        current.pop(key, None)
    _, success = await write_config(current, file_name)
    logger.info(f"批量配置键已删除: {list(keys)}")
    return current, success
