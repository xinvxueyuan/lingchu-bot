"""Test generation of handle configuration files.

This test verifies that the HandleConfigManager can generate valid JSON5
configuration files for the first 5 registered handles.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import aiofiles
import json5
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import (
    handle_config_manager as manager_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.core import schemas as schemas_module
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_defaults import (
    HANDLE_DEFAULTS_REGISTRY,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfigManager,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.schemas import (
    HANDLE_CONFIG_SCHEMA_BASENAME,
    HANDLE_CONFIG_SCHEMA_TEXT,
    install_schemas,
)


@pytest.fixture
def patched_localstore(
    tmp_path: Path,
) -> Iterator[Path]:
    """Redirect ``get_plugin_config_dir`` / ``get_plugin_config_file`` to ``tmp_path``.

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
def config_manager() -> HandleConfigManager:
    """Create a HandleConfigManager instance."""
    return HandleConfigManager()


@pytest.mark.asyncio
async def test_ensure_config_files_creates_all_handles(
    config_manager: HandleConfigManager,
    patched_localstore: Path,
):
    """Test that ensure_config_files creates configuration files for all registered handles."""
    # Install schemas first
    await install_schemas()

    # Ensure config files are created
    await config_manager.ensure_config_files()

    # Verify files exist
    for command_key in HANDLE_DEFAULTS_REGISTRY:
        file_path = patched_localstore / f"{command_key}.json5"
        assert file_path.exists(), (
            f"Config file for {command_key} should exist at {file_path}"
        )


@pytest.mark.asyncio
async def test_kick_member_config_content(patched_localstore: Path):
    """Test that kick_member.json5 has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "kick_member.json5"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = json5.loads(content)

    # Verify schema reference
    assert "$schema" in config_dict
    assert config_dict["$schema"] == HANDLE_CONFIG_SCHEMA_BASENAME

    # Verify enabled field
    assert "enabled" in config_dict
    assert config_dict["enabled"] is True

    # Verify defaults
    assert "defaults" in config_dict
    defaults = config_dict["defaults"]
    assert "require_reason" in defaults
    assert defaults["require_reason"] is False
    assert "audit_level" in defaults
    assert defaults["audit_level"] == "low"

    # Verify policies
    assert "policies" in config_dict
    assert isinstance(config_dict["policies"], dict)


@pytest.mark.asyncio
async def test_protect_member_config_content(patched_localstore: Path):
    """Test that protect_member.json5 has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "protect_member.json5"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = json5.loads(content)

    # Verify schema reference
    assert "$schema" in config_dict
    assert config_dict["$schema"] == HANDLE_CONFIG_SCHEMA_BASENAME

    # Verify enabled field
    assert "enabled" in config_dict
    assert config_dict["enabled"] is True

    # Verify defaults
    assert "defaults" in config_dict
    defaults = config_dict["defaults"]
    assert "whitelist_scope" in defaults
    assert defaults["whitelist_scope"] == "group"


@pytest.mark.asyncio
async def test_block_member_config_content(patched_localstore: Path):
    """Test that block_member.json5 has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "block_member.json5"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = json5.loads(content)

    # Verify schema reference
    assert "$schema" in config_dict
    assert config_dict["$schema"] == HANDLE_CONFIG_SCHEMA_BASENAME

    # Verify enabled field
    assert "enabled" in config_dict
    assert config_dict["enabled"] is True

    # Verify defaults
    assert "defaults" in config_dict
    defaults = config_dict["defaults"]
    assert "block_duration" in defaults
    assert defaults["block_duration"] is None
    assert "default_reason" in defaults
    assert defaults["default_reason"] == "违反群规"


@pytest.mark.asyncio
async def test_member_mute_config_content(patched_localstore: Path):
    """Test that member_mute.json5 has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "member_mute.json5"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = json5.loads(content)

    # Verify schema reference
    assert "$schema" in config_dict
    assert config_dict["$schema"] == HANDLE_CONFIG_SCHEMA_BASENAME

    # Verify enabled field
    assert "enabled" in config_dict
    assert config_dict["enabled"] is True

    # Verify defaults
    assert "defaults" in config_dict
    defaults = config_dict["defaults"]
    assert "mute_duration" in defaults
    assert defaults["mute_duration"] == 300
    assert "default_reason" in defaults
    assert defaults["default_reason"] == "管理员操作"


@pytest.mark.asyncio
async def test_recall_message_config_content(patched_localstore: Path):
    """Test that recall_message.json5 has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "recall_message.json5"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = json5.loads(content)

    # Verify schema reference
    assert "$schema" in config_dict
    assert config_dict["$schema"] == HANDLE_CONFIG_SCHEMA_BASENAME

    # Verify enabled field
    assert "enabled" in config_dict
    assert config_dict["enabled"] is True

    # Verify defaults
    assert "defaults" in config_dict
    defaults = config_dict["defaults"]
    assert "default_count" in defaults
    assert defaults["default_count"] == 10


async def test_schema_validation_for_all_handles(
    config_manager: HandleConfigManager,
    patched_localstore: Path,
):
    """Test that all generated configurations pass JSON Schema validation."""
    # Install schemas and ensure config files exist
    await install_schemas()
    await config_manager.ensure_config_files()

    schema = json.loads(HANDLE_CONFIG_SCHEMA_TEXT)

    for command_key in HANDLE_DEFAULTS_REGISTRY:
        file_path = patched_localstore / f"{command_key}.json5"
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        config_dict = json5.loads(content)

        # Validate using manager method
        is_valid = config_manager.validate_config(command_key, config_dict)
        assert is_valid, f"Config for {command_key} should pass schema validation"


async def test_json5_format_is_parseable(patched_localstore: Path):
    """Test that generated JSON5 files can be parsed by json5 library."""
    # Install schemas
    await install_schemas()

    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    for command_key in HANDLE_DEFAULTS_REGISTRY:
        file_path = patched_localstore / f"{command_key}.json5"
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()

        # Should parse without error
        config_dict = json5.loads(content)
        assert isinstance(config_dict, dict)


async def test_config_matches_defaults(patched_localstore: Path):
    """Test that generated configurations match registered defaults."""
    # Install schemas
    await install_schemas()

    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    for command_key, expected_defaults in HANDLE_DEFAULTS_REGISTRY.items():
        file_path = patched_localstore / f"{command_key}.json5"
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        config_dict = json5.loads(content)

        # Check that defaults match
        assert config_dict["defaults"] == expected_defaults["defaults"]
        assert config_dict["enabled"] == expected_defaults["enabled"]
        assert config_dict["policies"] == expected_defaults["policies"]
