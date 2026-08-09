"""Handle configuration manager backed by standard-library validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ..database.toml_store import (
    ensure_toml_dict_file_async,
    load_toml_dict_async,
    write_toml_dict_file_async,
)
from .handle_config_defaults import HANDLE_DEFAULTS_REGISTRY


@dataclass(frozen=True)
class HandleConfig:
    """Validated handle configuration data."""

    enabled: bool
    defaults: dict[str, Any]
    policies: dict[str, Any]


def _validate_config(raw: dict[str, Any]) -> dict[str, Any]:
    enabled = raw.get("enabled", True)
    defaults = raw.get("defaults", {})
    policies = raw.get("policies", {})
    if type(enabled) is not bool:
        raise ValueError("enabled must be a boolean")
    if not isinstance(defaults, dict) or not isinstance(policies, dict):
        raise TypeError("defaults and policies must be mappings")
    return {"enabled": enabled, "defaults": defaults, "policies": policies}


class HandleConfigManager:
    """Load, validate, cache, and persist handle configuration mappings."""

    _cache: ClassVar[dict[str, HandleConfig]] = {}

    async def get_config(self, command_key: str) -> HandleConfig:
        if command_key not in HANDLE_DEFAULTS_REGISTRY:
            raise ValueError(f"command_key not registered: {command_key}")
        if command_key in self._cache:
            return self._cache[command_key]
        default_config = HANDLE_DEFAULTS_REGISTRY[command_key]()
        file_path = get_plugin_config_file(f"{command_key}.toml")
        try:
            config_dict = await load_toml_dict_async(
                file_path, default=default_config, merge_default=True
            )
            config = self._build_handle_config(_validate_config(config_dict))
        except Exception:
            logger.error("Failed to load handle config for {}", command_key)
            config = self._build_handle_config(default_config)
        self._cache[command_key] = config
        return config

    async def update_config(self, command_key: str, updates: dict[str, Any]) -> None:
        if command_key not in HANDLE_DEFAULTS_REGISTRY:
            raise ValueError(f"command_key not registered: {command_key}")
        file_path = get_plugin_config_file(f"{command_key}.toml")
        defaults = HANDLE_DEFAULTS_REGISTRY[command_key]()
        try:
            config_dict = await load_toml_dict_async(
                file_path, default=defaults, merge_default=True
            )
        except Exception:
            config_dict = defaults
        for section, update in updates.items():
            if section in {"defaults", "policies"} and isinstance(update, dict):
                existing = config_dict.get(section, {})
                config_dict[section] = (
                    existing | update if isinstance(existing, dict) else update
                )
            else:
                config_dict[section] = update
        validated = _validate_config(config_dict)
        await write_toml_dict_file_async(file_path, validated)
        self._cache[command_key] = self._build_handle_config(validated)

    async def get_all_configs(self) -> dict[str, HandleConfig]:
        return {key: await self.get_config(key) for key in HANDLE_DEFAULTS_REGISTRY}

    async def ensure_config_files(self) -> None:
        for command_key, factory in HANDLE_DEFAULTS_REGISTRY.items():
            try:
                await ensure_toml_dict_file_async(
                    get_plugin_config_file(f"{command_key}.toml"), factory()
                )
            except Exception:
                logger.error("Failed to ensure handle config file for {}", command_key)

    def clear_cache(self) -> None:
        self._cache.clear()

    @staticmethod
    def _build_handle_config(raw: dict[str, Any]) -> HandleConfig:
        return HandleConfig(
            enabled=raw.get("enabled", True),
            defaults=dict(raw.get("defaults", {})),
            policies=dict(raw.get("policies", {})),
        )


__all__ = ["HandleConfig", "HandleConfigManager"]
