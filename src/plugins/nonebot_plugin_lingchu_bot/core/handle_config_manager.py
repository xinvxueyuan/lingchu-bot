"""Handle configuration manager for Lingchu Bot.

This module provides centralized management for handle-level configurations,
including loading, updating, validation, and persistence of handle configs.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, ClassVar, Final, cast

import jsonschema
from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ..database.toml_store import (
    ensure_toml_dict_file_async,
    load_toml_dict_async,
    write_toml_dict_file_async,
)
from .handle_config_defaults import HANDLE_DEFAULTS_REGISTRY
from .schemas import HANDLE_CONFIG_SCHEMA_BASENAME, HANDLE_CONFIG_SCHEMA_TEXT


@dataclass(frozen=True)
class HandleConfig:
    """Handle configuration data structure.

    Attributes:
        enabled: Whether this handle is enabled.
        defaults: Default values for handle-specific configuration fields.
        policies: Policy configuration for this handle.
    """

    enabled: bool
    defaults: dict[str, Any]
    policies: dict[str, Any]


class HandleConfigManager:
    """Manager for handle-level configurations.

    This class provides centralized access to handle configurations with
    automatic caching, fallback to defaults, and JSON Schema validation.

    The configuration priority is: code defaults < TOML file overrides.
    """

    _cache: ClassVar[dict[str, HandleConfig]] = {}
    _SCHEMA_REF: Final[str] = HANDLE_CONFIG_SCHEMA_BASENAME

    @staticmethod
    def _merge_registered_defaults(
        command_key: str, config_dict: dict[str, Any]
    ) -> dict[str, Any]:
        registered = HANDLE_DEFAULTS_REGISTRY[command_key]
        merged = dict(registered)
        merged.update(config_dict)
        for section in ("defaults", "policies"):
            registered_section = registered.get(section, {})
            loaded_section = config_dict.get(section, {})
            if isinstance(registered_section, dict) and isinstance(
                loaded_section, dict
            ):
                merged[section] = registered_section | loaded_section
        return merged

    async def get_config(self, command_key: str) -> HandleConfig:
        """Get handle configuration for a specific command.

        Loads configuration from the TOML file managed by localstore.
        Falls back to defaults from HANDLE_DEFAULTS_REGISTRY if the file
        does not exist or fails to load.

        Args:
            command_key: The unique identifier for the handle command.

        Returns:
            HandleConfig instance containing enabled, defaults, and policies.

        Raises:
            ValueError: If command_key is not registered in HANDLE_DEFAULTS_REGISTRY.
        """
        if command_key in self._cache:
            return self._cache[command_key]

        if command_key not in HANDLE_DEFAULTS_REGISTRY:
            raise ValueError(f"command_key not registered: {command_key}")

        file_path = get_plugin_config_file(f"{command_key}.toml")
        default_config = dict(HANDLE_DEFAULTS_REGISTRY[command_key])

        try:
            config_dict = await load_toml_dict_async(
                file_path,
                default=default_config,
                merge_default=True,
            )
            config_dict = self._merge_registered_defaults(command_key, config_dict)
        except Exception:
            logger.error(
                f"Failed to load handle config for {command_key}, "
                f"falling back to defaults. Path: {file_path}"
            )
            # Fallback to defaults
            config_dict = default_config

        # Extract fields with safe defaults and proper typing
        enabled = cast("bool", config_dict.get("enabled", True))
        defaults = cast("dict[str, Any]", config_dict.get("defaults", {}))
        policies = cast("dict[str, Any]", config_dict.get("policies", {}))

        config = HandleConfig(enabled=enabled, defaults=defaults, policies=policies)
        self._cache[command_key] = config
        return config

    async def update_config(self, command_key: str, updates: dict[str, Any]) -> None:
        """Update handle configuration with partial changes.

        Reads existing configuration, applies updates, validates against
        the JSON Schema, persists to disk, and updates the memory cache.

        Args:
            command_key: The unique identifier for the handle command.
            updates: Dictionary of partial updates to apply.

        Raises:
            ValueError: If command_key is not registered or validation fails.
            TOMLFileReadError: If file operations fail.
        """
        if command_key not in HANDLE_DEFAULTS_REGISTRY:
            raise ValueError(f"command_key not registered: {command_key}")

        file_path = get_plugin_config_file(f"{command_key}.toml")
        default_config = dict(HANDLE_DEFAULTS_REGISTRY[command_key])

        # Load existing config or use defaults
        try:
            config_dict = await load_toml_dict_async(
                file_path,
                default=default_config,
                merge_default=True,
            )
            config_dict = self._merge_registered_defaults(command_key, config_dict)
        except Exception:
            logger.error(
                f"Failed to load handle config for {command_key} during update, "
                f"using defaults. Path: {file_path}"
            )
            config_dict = default_config

        # Apply updates
        config_dict.update(updates)

        # Validate before persisting
        if not self.validate_config(command_key, config_dict):
            raise ValueError(f"validation failed: {command_key}")

        # Persist to disk
        await write_toml_dict_file_async(
            file_path,
            config_dict,
            schema_basename=self._SCHEMA_REF,
        )

        # Update cache
        enabled = cast("bool", config_dict.get("enabled", True))
        defaults = cast("dict[str, Any]", config_dict.get("defaults", {}))
        policies = cast("dict[str, Any]", config_dict.get("policies", {}))
        self._cache[command_key] = HandleConfig(
            enabled=enabled, defaults=defaults, policies=policies
        )

        logger.info(f"Handle config updated and persisted for {command_key}")

    async def get_all_configs(self) -> dict[str, HandleConfig]:
        """Get configurations for all registered handle commands.

        Returns:
            Dictionary mapping command_key to HandleConfig instances.
        """
        return {
            command_key: await self.get_config(command_key)
            for command_key in HANDLE_DEFAULTS_REGISTRY
        }

    async def ensure_config_files(self) -> None:
        """Ensure configuration files exist for all registered handles.

        Creates missing files with schema directives and default values.
        Existing files are not modified.
        """
        for command_key in HANDLE_DEFAULTS_REGISTRY:
            file_path = get_plugin_config_file(f"{command_key}.toml")
            defaults = HANDLE_DEFAULTS_REGISTRY[command_key]
            config_dict = dict(defaults)

            try:
                await ensure_toml_dict_file_async(
                    file_path,
                    config_dict,
                    schema_basename=self._SCHEMA_REF,
                )
                logger.debug(f"Ensured handle config file for {command_key}")
            except Exception:
                logger.error(
                    f"Failed to ensure handle config file for {command_key}. "
                    f"Path: {file_path}"
                )

    def validate_config(self, command_key: str, config_dict: dict[str, Any]) -> bool:
        """Validate handle configuration against JSON Schema.

        Args:
            command_key: The unique identifier for the handle command.
            config_dict: Configuration dictionary to validate.

        Returns:
            True if validation passes, False otherwise.

        Note:
            This method does not throw exceptions on validation failure.
            Errors are logged instead.
        """
        try:
            schema = json.loads(HANDLE_CONFIG_SCHEMA_TEXT)
            jsonschema.validate(config_dict, schema)
        except jsonschema.ValidationError as e:
            logger.error(
                f"Handle config validation failed for {command_key}: {e.message}"
            )
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schema JSON: {e}")
            return False
        except Exception:
            logger.error(f"Unexpected error during validation for {command_key}")
            return False
        else:
            return True

    def clear_cache(self) -> None:
        """Clear the internal configuration cache.

        Useful for forcing reload from disk after external modifications.
        """
        self._cache.clear()
        logger.debug("Handle config cache cleared")


__all__ = [
    "HandleConfig",
    "HandleConfigManager",
]
