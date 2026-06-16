"""Lightweight runtime configuration backed by JSON5 and NoneBot settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from nonebot import get_driver
from nonebot.compat import type_validate_python
from nonebot_plugin_localstore import get_plugin_config_file
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

if TYPE_CHECKING:
    from nonebot.config import Config as NoneBotConfig

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


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser: reads KEY=VALUE lines, ignores comments/blanks."""
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            result[key] = value
    return result


def _alias_map_from_model() -> dict[str, str]:
    """Build a mapping from validation alias to field name for RuntimeConfig."""
    alias_to_field: dict[str, str] = {}
    for field_name, field_info in RuntimeConfig.model_fields.items():
        if field_info.validation_alias is not None and isinstance(
            field_info.validation_alias, AliasChoices
        ):
            for alias in field_info.validation_alias.choices:
                if isinstance(alias, str):
                    alias_to_field[alias] = field_name
    return alias_to_field


def _global_config_overrides(global_config: NoneBotConfig) -> dict[str, Any]:
    """Extract alias-resolved values from NoneBot global_config."""
    dumped = global_config.model_dump()
    alias_to_field = _alias_map_from_model()
    result: dict[str, Any] = {}
    for source_key, target_field in alias_to_field.items():
        value = dumped.get(source_key)
        if value is None and hasattr(global_config, source_key):
            value = getattr(global_config, source_key)
        if value is not None:
            result[target_field] = value
    return result


def _dotenv_overrides(global_config: NoneBotConfig) -> dict[str, str]:
    """Read runtime config values from NoneBot's dotenv file."""
    env_file = getattr(global_config, "_env_file", None)
    if env_file is None:
        return {}
    # pydantic-settings _env_file can be a tuple of paths
    env_paths = env_file if isinstance(env_file, (list, tuple)) else [env_file]
    combined: dict[str, str] = {}
    for p in env_paths:
        combined.update(_parse_dotenv(Path(p)))
    return combined


def _coerce_env_value(raw: str, annotation: Any) -> Any:
    """Coerce a string env value to the expected Python type.

    Returns ``None`` when the value cannot be converted, so the caller
    will skip it and fall back to the default.
    """
    if annotation is bool:
        return raw.lower() in ("1", "true", "yes")
    try:
        if annotation is int:
            return int(raw)
        if annotation is float:
            return float(raw)
    except ValueError:
        return None
    return raw


def _env_overrides(dotenv_values: dict[str, str]) -> dict[str, Any]:
    """Collect env/dotenv overrides for all RuntimeConfig fields."""
    result: dict[str, Any] = {}
    for field_name, field_info in RuntimeConfig.model_fields.items():
        env_key = field_name.upper()
        raw = os.environ.get(env_key) or dotenv_values.get(env_key)
        if raw is not None:
            coerced = _coerce_env_value(raw, field_info.annotation)
            if coerced is not None:
                result[field_name] = coerced
    return result


def _nonebot_runtime_overrides() -> dict[str, Any]:
    """Extract runtime config overrides from NoneBot config and OS env vars.

    NoneBot's ``global_config`` contains values parsed from .env files and
    its own settings.  However, NoneBot only exposes fields it knows about
    (driver, superusers, plugin-declared configs, etc.).  Arbitrary
    environment variables like ``MESSAGE_STORE_SUMMARY_LIMIT`` are **not**
    reflected in ``global_config.model_dump()``.

    Priority (highest first):
    1. OS environment variables (``os.environ``)
    2. NoneBot dotenv file (``_env_file``)
    3. NoneBot ``global_config`` (for alias-resolved fields like lingchu_adapter)
    """
    try:
        global_config = get_driver().config
    except ValueError:
        global_config = None

    result: dict[str, Any] = {}

    if global_config is not None:
        result |= _global_config_overrides(global_config)
        dotenv_values = _dotenv_overrides(global_config)
    else:
        dotenv_values = {}

    result |= _env_overrides(dotenv_values)
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
