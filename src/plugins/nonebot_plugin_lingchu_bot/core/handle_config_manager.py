"""Handle configuration manager for Lingchu Bot.

This module provides centralized management for handle-level configurations,
including loading, updating, validation, and persistence of handle configs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Final, cast

from nonebot import logger, require
from nonebot.compat import type_validate_python
from pydantic import BaseModel, ValidationError

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ..database.toml_store import (
    ensure_toml_dict_file_async,
    load_toml_dict_async,
    write_toml_dict_file_async,
)
from .handle_config_defaults import HANDLE_DEFAULTS_REGISTRY
from .schemas import HANDLE_CONFIG_SCHEMA_BASENAME


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
    automatic caching, fallback to defaults, and pydantic-based validation.

    The configuration priority is: code defaults < TOML file overrides.
    Each handle's pydantic model (registered in ``HANDLE_DEFAULTS_REGISTRY``)
    declares field defaults that are used when the TOML file is missing
    fields, and validates the merged configuration via
    ``type_validate_python``.
    """

    _cache: ClassVar[dict[str, HandleConfig]] = {}
    _SCHEMA_REF: Final[str] = HANDLE_CONFIG_SCHEMA_BASENAME

    async def get_config(self, command_key: str) -> HandleConfig:
        """Get handle configuration for a specific command.

        Loads configuration from the TOML file managed by localstore,
        merges it with the pydantic model defaults, and validates the
        result via ``type_validate_python``. Falls back to the model
        defaults if the file is missing or fails to load/validate.

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

        model_cls = HANDLE_DEFAULTS_REGISTRY[command_key]
        file_path = get_plugin_config_file(f"{command_key}.toml")
        default_config = model_cls().model_dump(mode="json")

        try:
            config_dict = await load_toml_dict_async(
                file_path,
                default=default_config,
                merge_default=True,
            )
            model = type_validate_python(model_cls, config_dict)
        except Exception:
            logger.error(
                f"Failed to load handle config for {command_key}, "
                f"falling back to defaults. Path: {file_path}"
            )
            model = model_cls()

        config = self._build_handle_config(model)
        self._cache[command_key] = config
        return config

    async def update_config(self, command_key: str, updates: dict[str, Any]) -> None:
        """Update handle configuration with partial changes.

        Reads existing configuration, applies shallow updates, validates the
        merged result via ``type_validate_python``, persists the validated
        configuration to disk, and updates the memory cache.

        Args:
            command_key: The unique identifier for the handle command.
            updates: Dictionary of partial updates to apply. Top-level keys
                (``enabled``, ``defaults``, ``policies``) replace the
                existing values shallowly; nested defaults are re-merged
                by the pydantic model's field defaults during validation.

        Raises:
            ValueError: If command_key is not registered or validation fails.
            TOMLFileReadError: If file operations fail.
        """
        if command_key not in HANDLE_DEFAULTS_REGISTRY:
            raise ValueError(f"command_key not registered: {command_key}")

        model_cls = HANDLE_DEFAULTS_REGISTRY[command_key]
        file_path = get_plugin_config_file(f"{command_key}.toml")
        default_config = model_cls().model_dump(mode="json")

        # Load existing config or use defaults
        try:
            config_dict = await load_toml_dict_async(
                file_path,
                default=default_config,
                merge_default=True,
            )
        except Exception:
            logger.error(
                f"Failed to load handle config for {command_key} during update, "
                f"using defaults. Path: {file_path}"
            )
            config_dict = default_config

        # Apply updates (shallow)
        config_dict.update(updates)

        # Validate via pydantic before persisting
        try:
            model = type_validate_python(model_cls, config_dict)
        except ValidationError as exc:
            raise ValueError(f"validation failed: {command_key}") from exc

        # Persist validated configuration to disk
        validated_dict = model.model_dump(mode="json")
        await write_toml_dict_file_async(
            file_path,
            validated_dict,
            schema_basename=self._SCHEMA_REF,
        )

        # Update cache
        self._cache[command_key] = self._build_handle_config(model)

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

        Creates missing files with schema directives and default values
        derived from each handle's pydantic model. Existing files are
        not modified.
        """
        for command_key, model_cls in HANDLE_DEFAULTS_REGISTRY.items():
            file_path = get_plugin_config_file(f"{command_key}.toml")
            config_dict = model_cls().model_dump(mode="json")

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

    def clear_cache(self) -> None:
        """Clear the internal configuration cache.

        Useful for forcing reload from disk after external modifications.
        """
        self._cache.clear()
        logger.debug("Handle config cache cleared")

    @staticmethod
    def _build_handle_config(model: BaseModel) -> HandleConfig:
        """Build a ``HandleConfig`` dataclass from a validated pydantic model.

        Args:
            model: A validated pydantic model instance with ``enabled``,
                ``defaults``, and ``policies`` fields.

        Returns:
            A frozen ``HandleConfig`` dataclass populated from the model.
        """
        dumped: dict[str, Any] = model.model_dump(mode="json")
        return HandleConfig(
            enabled=cast("bool", dumped.get("enabled", True)),
            defaults=cast("dict[str, Any]", dumped.get("defaults", {})),
            policies=cast("dict[str, Any]", dumped.get("policies", {})),
        )


__all__ = [
    "HandleConfig",
    "HandleConfigManager",
]
