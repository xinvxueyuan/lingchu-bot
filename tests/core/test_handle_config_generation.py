"""Test generation of handle configuration files.

This test verifies that the HandleConfigManager can generate valid TOML
configuration files for the first 5 registered handles.
"""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import aiofiles
import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.core import (
    handle_config_manager as manager_module,
    schemas as schemas_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_defaults import (
    HANDLE_DEFAULTS_REGISTRY,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfigManager,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.schemas import (
    HANDLE_CONFIG_SCHEMA_BASENAME,
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
        file_path = patched_localstore / f"{command_key}.toml"
        assert file_path.exists(), (
            f"Config file for {command_key} should exist at {file_path}"
        )


@pytest.mark.asyncio
async def test_kick_member_config_content(patched_localstore: Path):
    """Test that kick_member.toml has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "kick_member.toml"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = rtoml.loads(content)

    assert content.startswith(f"#:schema ./{HANDLE_CONFIG_SCHEMA_BASENAME}\n")
    assert "$schema" not in config_dict

    # Verify enabled field
    assert "enabled" in config_dict
    assert config_dict["enabled"] is True

    # Verify defaults
    assert "defaults" in config_dict
    defaults = config_dict["defaults"]
    assert "require_reason" in defaults
    assert defaults["require_reason"] is False
    assert "audit_level" not in defaults

    # Verify policies
    assert "policies" in config_dict
    assert isinstance(config_dict["policies"], dict)


@pytest.mark.asyncio
async def test_protect_member_config_content(patched_localstore: Path):
    """Test that protect_member.toml has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "protect_member.toml"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = rtoml.loads(content)

    assert content.startswith(f"#:schema ./{HANDLE_CONFIG_SCHEMA_BASENAME}\n")
    assert "$schema" not in config_dict

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
    """Test that block_member.toml has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "block_member.toml"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = rtoml.loads(content)

    assert content.startswith(f"#:schema ./{HANDLE_CONFIG_SCHEMA_BASENAME}\n")
    assert "$schema" not in config_dict

    # Verify enabled field
    assert "enabled" in config_dict
    assert config_dict["enabled"] is True

    # Verify defaults
    assert "defaults" in config_dict
    defaults = config_dict["defaults"]
    assert "block_duration" not in defaults
    assert "default_reason" in defaults
    assert defaults["default_reason"] == "违反群规"


@pytest.mark.asyncio
async def test_member_mute_config_content(patched_localstore: Path):
    """Test that member_mute.toml has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "member_mute.toml"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = rtoml.loads(content)

    assert content.startswith(f"#:schema ./{HANDLE_CONFIG_SCHEMA_BASENAME}\n")
    assert "$schema" not in config_dict

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
    """Test that recall_message.toml has the expected content."""
    # Install schemas first
    await install_schemas()

    # Ensure file exists
    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    file_path = patched_localstore / "recall_message.toml"

    # Load and verify content
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    config_dict = rtoml.loads(content)

    assert content.startswith(f"#:schema ./{HANDLE_CONFIG_SCHEMA_BASENAME}\n")
    assert "$schema" not in config_dict

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

    for command_key in HANDLE_DEFAULTS_REGISTRY:
        file_path = patched_localstore / f"{command_key}.toml"
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        config_dict = rtoml.loads(content)

        # Validate using manager method
        is_valid = config_manager.validate_config(command_key, config_dict)
        assert is_valid, f"Config for {command_key} should pass schema validation"


async def test_toml_format_is_parseable(patched_localstore: Path):
    """Test that generated TOML files can be parsed by toml library."""
    # Install schemas
    await install_schemas()

    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    for command_key in HANDLE_DEFAULTS_REGISTRY:
        file_path = patched_localstore / f"{command_key}.toml"
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()

        # Should parse without error
        config_dict = rtoml.loads(content)
        assert isinstance(config_dict, dict)


async def test_config_matches_defaults(patched_localstore: Path):
    """Test that generated configurations match registered defaults."""
    # Install schemas
    await install_schemas()

    config_manager = HandleConfigManager()
    await config_manager.ensure_config_files()

    for command_key, expected_defaults in HANDLE_DEFAULTS_REGISTRY.items():
        file_path = patched_localstore / f"{command_key}.toml"
        async with aiofiles.open(file_path, encoding="utf-8") as f:
            content = await f.read()
        config_dict = rtoml.loads(content)

        # Check that defaults match
        expected_on_disk = rtoml.loads(
            rtoml.dumps(expected_defaults, pretty=True, none_value=None)
        )
        assert config_dict["defaults"] == expected_on_disk["defaults"]
        assert config_dict["enabled"] == expected_defaults["enabled"]
        assert config_dict["policies"] == expected_defaults["policies"]


def test_chat_is_not_in_handle_defaults_registry() -> None:
    """Chat command was extracted to llm_chat subplugin; it must not be in handle defaults."""
    assert "chat" not in HANDLE_DEFAULTS_REGISTRY


def test_novelai_image_is_not_in_handle_defaults_registry() -> None:
    """novelai_image command is owned by its subplugin; it must not be in handle defaults."""
    assert "novelai_image" not in HANDLE_DEFAULTS_REGISTRY
