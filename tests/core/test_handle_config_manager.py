"""Test handle configuration manager functionality.

This test module covers the core functionality of HandleConfigManager,
including configuration loading, updating, validation, and persistence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import aiofiles
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import (
    handle_config_manager as manager_module,
    schemas as schemas_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_defaults import (
    HANDLE_DEFAULTS_REGISTRY,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_defaults.mass_announcement import (
    MassAnnouncementConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_defaults.restart_protocol_endpoint import (
    RestartProtocolEndpointConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfig,
    HandleConfigManager,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.schemas import install_schemas

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def patched_localstore(
    tmp_path: Path,
) -> Iterator[Path]:
    """Redirect ``get_plugin_config_file`` to ``tmp_path``.

    Returns the config_dir so individual tests can assert the precise target paths.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    def mock_get_plugin_config_file(filename: str) -> Path:
        """Mock get_plugin_config_file to return path in tmp_path."""
        return config_dir / filename

    with (
        patch.object(
            schemas_module,
            "get_plugin_config_dir",
            return_value=config_dir,
        ),
        patch.object(
            schemas_module,
            "get_plugin_data_dir",
            return_value=tmp_path / "data",
        ),
        patch.object(
            manager_module,
            "get_plugin_config_file",
            side_effect=mock_get_plugin_config_file,
        ),
    ):
        yield config_dir


@pytest.fixture
def config_manager() -> Iterator[HandleConfigManager]:
    """Create a HandleConfigManager instance."""
    manager = HandleConfigManager()
    manager.clear_cache()
    try:
        yield manager
    finally:
        manager.clear_cache()


def test_mass_announcement_defaults_are_registered() -> None:
    assert HANDLE_DEFAULTS_REGISTRY["mass_announcement"] is MassAnnouncementConfig
    instance = MassAnnouncementConfig()
    assert instance.enabled is True
    assert instance.defaults == {}
    assert instance.policies == {}


def test_restart_protocol_endpoint_defaults_are_registered() -> None:
    assert (
        HANDLE_DEFAULTS_REGISTRY["restart_protocol_endpoint"]
        is RestartProtocolEndpointConfig
    )
    instance = RestartProtocolEndpointConfig()
    assert instance.enabled is True
    assert instance.defaults == {}
    assert instance.policies == {}


# SubTask 8.1: HandleConfig dataclass 字段结构测试
class TestHandleConfigDataclass:
    """Test HandleConfig dataclass field structure."""

    def test_handle_config_creation(self) -> None:
        """Test that HandleConfig objects can be created with all required fields."""
        enabled = True
        defaults = {"require_reason": False, "audit_level": "low"}
        policies: dict[str, Any] = {}

        config = HandleConfig(enabled=enabled, defaults=defaults, policies=policies)

        assert config.enabled == enabled
        assert config.defaults == defaults
        assert config.policies == policies

    def test_handle_config_field_types(self) -> None:
        """Test that HandleConfig fields have correct types."""
        config = HandleConfig(
            enabled=True,
            defaults={"test_key": "test_value"},
            policies={"policy_key": "policy_value"},
        )

        assert isinstance(config.enabled, bool)
        assert isinstance(config.defaults, dict)
        assert isinstance(config.policies, dict)

    def test_handle_config_frozen(self) -> None:
        """Test that HandleConfig is frozen (immutable)."""
        config = HandleConfig(enabled=True, defaults={}, policies={})

        # Should raise AttributeError when trying to modify
        with pytest.raises(AttributeError):
            setattr(config, "enabled", False)  # noqa: B010 - intentional frozen-dataclass mutation test

    def test_handle_config_empty_defaults_and_policies(self) -> None:
        """Test that HandleConfig allows empty defaults and policies."""
        config = HandleConfig(enabled=False, defaults={}, policies={})

        assert config.enabled is False
        assert config.defaults == {}
        assert config.policies == {}


# SubTask 8.2: get_config 回退默认值测试
class TestGetConfigFallback:
    """Test get_config fallback to defaults."""

    async def test_get_config_returns_defaults_when_file_missing(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that get_config returns code defaults when config file is missing."""
        # Install schemas first
        await install_schemas()

        # Don't create config files, test fallback
        command_key = "kick_member"
        config = await config_manager.get_config(command_key)

        # Verify returned config matches defaults
        assert config.enabled is True
        assert "require_reason" in config.defaults
        assert config.defaults["require_reason"] is False
        assert "audit_level" in config.defaults
        assert config.defaults["audit_level"] == "low"
        assert config.policies == {}

    async def test_get_config_no_exception_when_file_missing(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that get_config does not throw exception when file is missing."""
        await install_schemas()

        # Should not raise any exception
        for command_key in HANDLE_DEFAULTS_REGISTRY:
            config = await config_manager.get_config(command_key)
            assert isinstance(config, HandleConfig)

    async def test_get_config_unregistered_command_key_raises_error(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that get_config raises ValueError for unregistered command_key."""
        with pytest.raises(ValueError, match="command_key not registered"):
            await config_manager.get_config("nonexistent_command")


# SubTask 8.3: update_config 持久化测试
@pytest.mark.asyncio
class TestUpdateConfigPersistence:
    """Test update_config persistence."""

    async def test_update_config_persists_to_file(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that update_config writes changes to disk."""
        await install_schemas()

        command_key = "kick_member"
        file_path = patched_localstore / f"{command_key}.toml"

        # Update configuration
        updates = {"enabled": False, "defaults": {"require_reason": True}}
        await config_manager.update_config(command_key, updates)

        # Verify file was created
        assert file_path.exists()

        # Read file content
        import rtoml

        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        config_dict = rtoml.loads(content)

        # Verify updates were persisted
        assert config_dict["enabled"] is False
        assert config_dict["defaults"]["require_reason"] is True

    async def test_update_config_reflected_in_memory(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that update_config updates in-memory cache."""
        await install_schemas()

        command_key = "kick_member"

        # Update configuration
        updates = {"enabled": False}
        await config_manager.update_config(command_key, updates)

        # Verify cache reflects update
        config = await config_manager.get_config(command_key)
        assert config.enabled is False

    async def test_update_config_partial_update(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that update_config supports partial updates."""
        await install_schemas()

        command_key = "kick_member"

        # First update: set enabled to False
        await config_manager.update_config(command_key, {"enabled": False})

        # Second update: only change defaults
        await config_manager.update_config(
            command_key, {"defaults": {"require_reason": True, "audit_level": "high"}}
        )

        # Verify enabled is still False
        config = await config_manager.get_config(command_key)
        assert config.enabled is False
        assert config.defaults["require_reason"] is True
        assert config.defaults["audit_level"] == "high"


# SubTask 8.4: ensure_config_files 创建缺失文件测试
@pytest.mark.asyncio
class TestEnsureConfigFiles:
    """Test ensure_config_files creates missing files."""

    async def test_creates_all_missing_config_files(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that ensure_config_files creates files for all registered handles."""
        await install_schemas()

        # Ensure no config files exist
        for command_key in HANDLE_DEFAULTS_REGISTRY:
            file_path = patched_localstore / f"{command_key}.toml"
            assert not file_path.exists()

        # Run ensure_config_files
        await config_manager.ensure_config_files()

        # Verify all files were created
        for command_key in HANDLE_DEFAULTS_REGISTRY:
            file_path = patched_localstore / f"{command_key}.toml"
            assert file_path.exists(), f"Config file for {command_key} should exist"

    async def test_creates_files_with_correct_content(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that ensure_config_files creates files with correct default content."""
        await install_schemas()

        await config_manager.ensure_config_files()

        import rtoml

        for command_key, model_cls in HANDLE_DEFAULTS_REGISTRY.items():
            expected_defaults = model_cls().model_dump(mode="json")
            file_path = patched_localstore / f"{command_key}.toml"
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()
            config_dict = rtoml.loads(content)

            # Verify content matches defaults
            assert content.startswith("#:schema ./handle_config.schema.json\n")
            assert config_dict["enabled"] == expected_defaults["enabled"]
            expected_on_disk = rtoml.loads(
                rtoml.dumps(expected_defaults, pretty=True, none_value=None)
            )
            assert config_dict["defaults"] == expected_on_disk["defaults"]
            assert config_dict["policies"] == expected_defaults["policies"]

    async def test_does_not_modify_existing_files(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that ensure_config_files does not modify existing files."""
        await install_schemas()

        command_key = "kick_member"
        file_path = patched_localstore / f"{command_key}.toml"

        # Create a file with custom content
        import rtoml

        custom_content = {
            "enabled": False,
            "defaults": {"require_reason": True, "audit_level": "high"},
            "policies": {"custom_policy": "value"},
        }
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(rtoml.dumps(custom_content, pretty=True))

        # Run ensure_config_files
        await config_manager.ensure_config_files()

        # Verify file was not modified
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        config_dict = rtoml.loads(content)

        assert config_dict["enabled"] is False
        assert config_dict["defaults"]["require_reason"] is True
        assert config_dict["policies"]["custom_policy"] == "value"


# SubTask 10.2: pydantic 校验路径测试（替代原 validate_config 方法）
@pytest.mark.asyncio
class TestPydanticValidation:
    """Test pydantic validation through update_config."""

    async def test_update_config_rejects_invalid_defaults_type(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that update_config raises ValueError when defaults has wrong type."""
        await install_schemas()

        command_key = "kick_member"
        invalid_updates: dict[str, Any] = {
            "enabled": True,
            "defaults": "not-a-dict",  # Should be a dict, not a string
            "policies": {},
        }

        with pytest.raises(ValueError, match="validation failed"):
            await config_manager.update_config(command_key, invalid_updates)

    async def test_update_config_accepts_valid_config(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that update_config accepts a valid full configuration."""
        await install_schemas()

        command_key = "kick_member"
        valid_updates = {
            "enabled": False,
            "defaults": {"require_reason": True, "audit_level": "high"},
            "policies": {"custom": "value"},
        }

        await config_manager.update_config(command_key, valid_updates)
        config = await config_manager.get_config(command_key)
        assert config.enabled is False
        assert config.defaults["require_reason"] is True
        assert config.defaults["audit_level"] == "high"
        assert config.policies["custom"] == "value"

    async def test_update_config_fills_missing_defaults_fields(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that pydantic fills in missing defaults fields from model defaults."""
        await install_schemas()

        command_key = "kick_member"
        # Only provide one defaults field; pydantic should fill audit_level
        await config_manager.update_config(
            command_key, {"defaults": {"require_reason": True}}
        )

        config = await config_manager.get_config(command_key)
        assert config.defaults["require_reason"] is True
        assert config.defaults["audit_level"] == "low"


# SubTask 8.6: 配置更新不影响其他模块测试
@pytest.mark.asyncio
class TestConfigIsolation:
    """Test that updating one config does not affect other configs."""

    async def test_update_kick_member_does_not_affect_block_member(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that updating kick_member config does not change block_member config."""
        await install_schemas()

        # Ensure all config files exist
        await config_manager.ensure_config_files()

        # Update kick_member config
        await config_manager.update_config("kick_member", {"enabled": False})

        # Verify block_member config is unchanged
        block_config = await config_manager.get_config("block_member")
        assert block_config.enabled is True
        assert block_config.defaults["block_duration"] is None
        assert block_config.defaults["default_reason"] == "违反群规"

    async def test_update_one_command_does_not_affect_others(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that updating one command config does not affect other configs."""
        await install_schemas()

        # Ensure all config files exist
        await config_manager.ensure_config_files()

        # Get initial configs
        initial_configs = await config_manager.get_all_configs()

        # Update one config
        await config_manager.update_config("member_mute", {"enabled": False})

        # Verify other configs are unchanged
        for command_key in HANDLE_DEFAULTS_REGISTRY:
            if command_key == "member_mute":
                continue

            current_config = await config_manager.get_config(command_key)
            initial_config = initial_configs[command_key]

            assert current_config.enabled == initial_config.enabled
            assert current_config.defaults == initial_config.defaults
            assert current_config.policies == initial_config.policies


# SubTask 8.7: enabled=False 拒绝执行测试
class TestEnabledFalseBehavior:
    """Test behavior when enabled=False."""

    async def test_get_config_returns_disabled_state(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that get_config correctly returns disabled state."""
        await install_schemas()

        # Create config file with enabled=False
        await config_manager.ensure_config_files()
        await config_manager.update_config("kick_member", {"enabled": False})

        # Verify get_config returns disabled state
        config = await config_manager.get_config("kick_member")
        assert config.enabled is False

    async def test_can_check_enabled_state_before_execution(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that callers can check enabled state before executing handle logic."""
        await install_schemas()

        # Create config with enabled=False
        await config_manager.ensure_config_files()
        await config_manager.update_config("kick_member", {"enabled": False})

        # Simulate handle logic checking enabled state
        config = await config_manager.get_config("kick_member")
        # Return False when disabled (reject execution), True otherwise
        result = config.enabled
        assert result is False, "Handle should be rejected when enabled=False"

    @pytest.mark.asyncio
    async def test_enabled_state_persists_across_cache_clear(
        self,
        config_manager: HandleConfigManager,
        patched_localstore: Path,
    ) -> None:
        """Test that enabled state persists after cache clear."""
        await install_schemas()

        # Set enabled=False
        await config_manager.ensure_config_files()
        await config_manager.update_config("kick_member", {"enabled": False})

        # Clear cache
        config_manager.clear_cache()

        # Verify enabled state persists
        config = await config_manager.get_config("kick_member")
        assert config.enabled is False
