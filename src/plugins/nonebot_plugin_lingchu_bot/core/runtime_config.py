"""Lightweight runtime configuration backed by JSON5 and NoneBot settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from nonebot import get_driver
from nonebot.compat import type_validate_python
from nonebot_plugin_localstore import get_plugin_config_file
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

from ..database.json5_store import (
    DatabaseError,
    ensure_json5_dict_file_sync,
    load_json5_dict_sync,
)

CONFIG_FILENAME: Final = "config.json5"


class RuntimeConfigError(RuntimeError):
    """轻量运行配置加载失败。"""

    def __init__(self, config_file: Path, reason: BaseException) -> None:
        self.config_file = config_file
        super().__init__(f"Invalid Lingchu runtime config {config_file}: {reason}")


class RuntimeConfig(BaseModel):
    """Lingchu Bot lightweight runtime settings.

    JSON5 values provide low-priority defaults. NoneBot direct config,
    environment variables and dotenv files override them through NoneBot's own
    settings parser.
    """

    superuser_key: str = "123456789abcdef"
    message_store_enabled: bool = True
    message_store_retention_days: int = Field(default=30, ge=0)
    message_store_summary_limit: int = Field(default=500, ge=0)
    message_store_record_api_calls: bool = True
    message_store_cleanup_enabled: bool = True
    lingchu_adapter: str | list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "lingchu_adapter",
            "LINGCHUAdapter",
            "LINGCHU_ADAPTER",
        ),
    )

    model_config = ConfigDict(extra="ignore")


def runtime_config_defaults() -> dict[str, Any]:
    """Return validated code defaults for the generated JSON5 file."""
    return RuntimeConfig().model_dump(mode="python")


def get_runtime_config_file() -> Path:
    """Return the localstore-backed runtime config file path."""
    try:
        return get_plugin_config_file(CONFIG_FILENAME)
    except ValueError:
        return Path(CONFIG_FILENAME)


def load_runtime_json_defaults(
    config_file: str | Path | None = None,
) -> dict[str, Any]:
    """Load low-priority runtime defaults from JSON5."""
    path = Path(config_file) if config_file is not None else get_runtime_config_file()
    try:
        return load_json5_dict_sync(path, default={}, merge_default=False)
    except DatabaseError as exc:
        raise RuntimeConfigError(path, exc) from exc


def _nonebot_runtime_overrides() -> dict[str, Any]:
    """Extract lingchu_adapter value from NoneBot global config.

    NoneBot has already parsed .env files and OS environment variables into
    ``global_config``, so re-reading dotenv via private APIs would be redundant.
    We simply extract the relevant key(s) from the already-parsed config.
    """
    try:
        global_config = get_driver().config
    except ValueError:
        return {}

    dumped = global_config.model_dump()
    result: dict[str, Any] = {}
    for key in (
        "lingchu_adapter",
        "LINGCHUAdapter",
        "LINGCHU_ADAPTER",
        "lingchuadapter",
    ):
        value = dumped.get(key)
        if value is not None:
            result[key] = value
        elif hasattr(global_config, key):
            attr = getattr(global_config, key)
            if attr is not None:
                result[key] = attr
    return result


def _normalize_runtime_aliases(values: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(values)
    for alias in ("LINGCHUAdapter", "LINGCHU_ADAPTER", "lingchuadapter"):
        value = normalized.pop(alias, None)
        if value is not None:
            normalized["lingchu_adapter"] = value
    return normalized


def get_runtime_config(
    config_file: str | Path | None = None,
) -> RuntimeConfig:
    """Resolve runtime config with OS env > dotenv > JSON5 > code defaults."""
    path = Path(config_file) if config_file is not None else get_runtime_config_file()
    raw_config = runtime_config_defaults() | load_runtime_json_defaults(path)
    raw_config |= _nonebot_runtime_overrides()
    raw_config = _normalize_runtime_aliases(raw_config)
    try:
        return type_validate_python(RuntimeConfig, raw_config)
    except ValidationError as exc:
        raise RuntimeConfigError(path, exc) from exc


def ensure_runtime_config_file(
    config_file: str | Path | None = None,
) -> Path:
    """Create the default JSON5 runtime config file on first startup."""
    path = Path(config_file) if config_file is not None else get_runtime_config_file()
    try:
        return ensure_json5_dict_file_sync(path, runtime_config_defaults())
    except DatabaseError as exc:
        raise RuntimeConfigError(path, exc) from exc


runtime_config: RuntimeConfig = get_runtime_config()
