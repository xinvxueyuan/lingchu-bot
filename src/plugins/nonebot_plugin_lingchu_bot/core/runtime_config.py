"""Lightweight runtime configuration backed by TOML and NoneBot settings."""

# ruff: noqa: TRY003

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal

from nonebot import get_driver, require
from nonebot.compat import type_validate_python

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

if TYPE_CHECKING:
    from nonebot.config import Config as NoneBotConfig

from ..database.toml_store import (
    DatabaseError,
    ensure_toml_dict_file_async,
    ensure_toml_dict_file_sync,
    load_toml_dict_sync,
)
from .handle_config_defaults import HANDLE_DEFAULTS_REGISTRY  # noqa: F401
from .handle_config_manager import HandleConfigManager
from .schemas import CONFIG_SCHEMA_BASENAME

CONFIG_FILENAME: Final = "config.toml"


class RuntimeConfigError(RuntimeError):
    """轻量运行配置加载失败。"""

    def __init__(self, config_file: Path, reason: BaseException) -> None:
        self.config_file = config_file
        super().__init__(f"Invalid Lingchu runtime config {config_file}: {reason}")


class RuntimeConfig(BaseModel):
    """Lingchu Bot lightweight runtime settings.

    TOML values provide low-priority defaults. NoneBot direct config,
    environment variables and dotenv files override them through NoneBot's own
    settings parser.
    """

    superuser_key: str = Field(
        default="123456789abcdef",
        validation_alias=AliasChoices("LINGCHU_SUPERUSER_KEY", "superuser_key"),
    )
    message_store_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_ENABLED",
            "message_store_enabled",
        ),
    )
    message_store_retention_days: int = Field(
        default=30,
        ge=0,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_RETENTION_DAYS",
            "message_store_retention_days",
        ),
    )
    message_store_summary_limit: int = Field(
        default=500,
        ge=0,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT",
            "message_store_summary_limit",
        ),
    )
    message_store_record_api_calls: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_RECORD_API_CALLS",
            "message_store_record_api_calls",
        ),
    )
    message_store_cleanup_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_CLEANUP_ENABLED",
            "message_store_cleanup_enabled",
        ),
    )
    ai_provider: Literal["litellm", "openai"] = Field(
        default="litellm",
        validation_alias=AliasChoices("LINGCHU_AI_PROVIDER", "ai_provider"),
    )
    ai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("LINGCHU_AI_MODEL", "ai_model"),
    )
    ai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINGCHU_AI_BASE_URL", "ai_base_url"),
    )
    ai_timeout: float = Field(
        default=60.0,
        gt=0,
        validation_alias=AliasChoices("LINGCHU_AI_TIMEOUT", "ai_timeout"),
    )
    ai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINGCHU_AI_API_KEY", "ai_api_key"),
    )
    recall_message_default_count: int = Field(
        default=10,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "LINGCHU_RECALL_MESSAGE_DEFAULT_COUNT",
            "recall_message_default_count",
        ),
    )
    permission_platform_runtime_passthrough: bool | dict[str, bool] = Field(
        default=True,
        validation_alias=AliasChoices(
            "LINGCHU_PERMISSION_PLATFORM_RUNTIME_PASSTHROUGH",
            "permission_platform_runtime_passthrough",
        ),
    )
    command_trigger_overrides: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "LINGCHU_COMMAND_TRIGGER_OVERRIDES",
            "command_trigger_overrides",
        ),
    )
    menu_page_trigger_overrides: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "LINGCHU_MENU_PAGE_TRIGGER_OVERRIDES",
            "menu_page_trigger_overrides",
        ),
    )
    protected_subject_feature_keys: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "kick_member",
                "block_member",
                "global_block_member",
                "member_mute",
                "recall_message",
                "set_member_card",
                "set_member_title",
                "set_member_admin",
                "unset_member_admin",
                "remote_kick",
                "remote_block",
                "remote_mute",
            }
        ),
        validation_alias=AliasChoices(
            "LINGCHU_PROTECTED_SUBJECT_FEATURE_KEYS",
            "protected_subject_feature_keys",
        ),
    )
    lingchu_superusers: dict[str, dict[str, str | int]] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "lingchu_superusers",
            "LINGCHU_SUPERUSERS",
        ),
    )
    lingchu_adapter: str | list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "lingchu_adapter",
        ),
    )

    model_config = ConfigDict(extra="ignore")

    @field_validator("lingchu_superusers", mode="before")
    @classmethod
    def _validate_lingchu_superusers(  # noqa: C901
        cls,
        value: Any,
    ) -> dict[str, dict[str, str | int]] | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise ValueError("LINGCHU_SUPERUSERS must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("LINGCHU_SUPERUSERS must be a mapping")  # noqa: TRY004
        result: dict[str, dict[str, str | int]] = {}
        for uid, accounts in value.items():
            uid_text = str(uid).strip()
            if not uid_text:
                raise ValueError("LINGCHU_SUPERUSERS UID cannot be empty")
            if not isinstance(accounts, dict):
                raise ValueError(  # noqa: TRY004
                    "LINGCHU_SUPERUSERS account value must be a mapping"
                )
            result[uid_text] = {}
            for platform_id, account_id in accounts.items():
                platform_text = str(platform_id).strip()
                if not platform_text:
                    raise ValueError("LINGCHU_SUPERUSERS platform cannot be empty")
                if not isinstance(account_id, (str, int)):
                    raise ValueError(  # noqa: TRY004
                        "LINGCHU_SUPERUSERS account id must be str or int"
                    )
                result[uid_text][platform_text] = account_id
        return result

    @field_validator("protected_subject_feature_keys", mode="before")
    @classmethod
    def _validate_protected_subject_feature_keys(cls, value: Any) -> frozenset[str]:
        if value is None:
            return frozenset()
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                value = [value]
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise TypeError("protected_subject_feature_keys must be a list")
        return frozenset(str(item).strip() for item in value if str(item).strip())


def runtime_config_defaults() -> dict[str, Any]:
    """Return validated code defaults for the generated TOML file."""
    return RuntimeConfig().model_dump(mode="json")


def get_runtime_config_file() -> Path:
    """Return the localstore-backed runtime config file path."""
    try:
        return get_plugin_config_file(CONFIG_FILENAME)
    except ValueError:
        return Path(CONFIG_FILENAME)


def load_runtime_toml_defaults(
    config_file: str | Path | None = None,
) -> dict[str, Any]:
    """Load low-priority runtime defaults from TOML."""
    path = Path(config_file) if config_file is not None else get_runtime_config_file()
    try:
        # Import-time sync I/O: no event loop exists yet at module load.
        return load_toml_dict_sync(path, default={}, merge_default=False)
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
    """Collect env/dotenv overrides for all RuntimeConfig fields.

    Only ``LINGCHU_``-prefixed env keys are read. Fields whose name already
    starts with ``lingchu_`` (e.g. ``lingchu_superusers``) use the field name
    uppercased as the env key (``LINGCHU_SUPERUSERS``) without an extra
    ``LINGCHU_`` prefix so no ``LINGCHU_LINGCHU_*`` doubling occurs.
    """
    result: dict[str, Any] = {}
    for field_name, field_info in RuntimeConfig.model_fields.items():
        if field_name.startswith("lingchu_"):
            env_key = field_name.upper()
        else:
            env_key = f"LINGCHU_{field_name.upper()}"

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
    environment variables like ``LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT`` are **not**
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


def get_runtime_config(
    config_file: str | Path | None = None,
) -> RuntimeConfig:
    """Resolve runtime config with OS env > dotenv > TOML > code defaults."""
    path = Path(config_file) if config_file is not None else get_runtime_config_file()
    raw_config = runtime_config_defaults() | load_runtime_toml_defaults(path)
    raw_config |= _nonebot_runtime_overrides()
    try:
        return type_validate_python(RuntimeConfig, raw_config)
    except ValidationError as exc:
        raise RuntimeConfigError(path, exc) from exc


def ensure_runtime_config_file(
    config_file: str | Path | None = None,
) -> Path:
    """Create the default TOML runtime config file on first startup."""
    path = Path(config_file) if config_file is not None else get_runtime_config_file()
    try:
        # Sync I/O: import-time API; runtime uses ensure_runtime_config_file_async.
        return ensure_toml_dict_file_sync(
            path,
            runtime_config_defaults(),
            schema_basename=CONFIG_SCHEMA_BASENAME,
        )
    except DatabaseError as exc:
        raise RuntimeConfigError(path, exc) from exc


async def ensure_runtime_config_file_async(
    config_file: str | Path | None = None,
) -> Path:
    """Async variant of :func:`ensure_runtime_config_file`.

    Uses ``aiofiles`` for non-blocking I/O so it can be awaited from
    ``startup()`` inside the event loop.
    """
    path = Path(config_file) if config_file is not None else get_runtime_config_file()
    try:
        return await ensure_toml_dict_file_async(
            path,
            runtime_config_defaults(),
            schema_basename=CONFIG_SCHEMA_BASENAME,
        )
    except DatabaseError as exc:
        raise RuntimeConfigError(path, exc) from exc


runtime_config: RuntimeConfig = get_runtime_config()


# Handle configuration manager singleton and factory functions
# Placed at the end of the file to avoid triggering initialization during module import

_handle_config_manager: HandleConfigManager | None = None


def get_handle_config_manager() -> HandleConfigManager:
    """Get the global handle configuration manager singleton.

    Uses lazy initialization: creates the HandleConfigManager instance on
    first call and caches it for subsequent calls.

    Returns:
        HandleConfigManager: The global singleton instance for managing
            handle-level configurations.

    Note:
        This function is safe to call multiple times; it always returns
        the same instance after the first initialization.

    Example:
        >>> manager = get_handle_config_manager()
        >>> config = await manager.get_config("kick_member")
    """
    global _handle_config_manager  # noqa: PLW0603
    if _handle_config_manager is None:
        _handle_config_manager = HandleConfigManager()
    return _handle_config_manager


async def initialize_handle_config_manager() -> None:
    """Initialize the handle configuration manager during startup.

    This function ensures all handle configuration files exist and preloads
    them into the memory cache. It should be called during the bot startup
    phase to prepare the configuration system.

    The initialization process:
    1. Ensures configuration files exist for all registered handles
    2. Loads all configurations into memory cache

    Raises:
        No exceptions are raised; errors are logged and non-fatal.

    Note:
        This function is non-blocking and safe to call from async context.
        If files cannot be created or loaded, the manager falls back to
        defaults from HANDLE_DEFAULTS_REGISTRY.

    Example:
        >>> async def startup():
        >>>     await initialize_handle_config_manager()
        >>>     # All handle configs are now ready
    """
    manager = get_handle_config_manager()
    await manager.ensure_config_files()
    # Preload all configs into cache
    await manager.get_all_configs()


__all__ = [
    "RuntimeConfig",
    "RuntimeConfigError",
    "ensure_runtime_config_file",
    "ensure_runtime_config_file_async",
    "get_handle_config_manager",
    "get_runtime_config",
    "get_runtime_config_file",
    "initialize_handle_config_manager",
    "load_runtime_toml_defaults",
    "runtime_config",
    "runtime_config_defaults",
]
