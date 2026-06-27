"""Generate handle configuration files for Lingchu Bot.

This script creates the first 5 handle configuration JSON5 files
in the localstore-managed config directory.
"""

import asyncio
import sys
from pathlib import Path

import json5
import nonebot

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Initialize NoneBot first
nonebot.init(LOCALSTORE_USE_CWD=True)

from nonebot_plugin_localstore import get_plugin_config_dir, get_plugin_config_file

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


def generate_handle_configs() -> None:
    """Generate handle configuration files for all registered handles."""
    # Install schemas first
    print("Installing schemas...")
    install_schemas()

    # Create HandleConfigManager
    print("Creating HandleConfigManager...")
    manager = HandleConfigManager()

    # Ensure config files exist (using synchronous approach since we're in a script)
    print("Ensuring configuration files...")
    asyncio.run(manager.ensure_config_files())

    # Get config directory
    config_dir = get_plugin_config_dir()
    print(f"\nConfig directory: {config_dir}")

    # Verify and display generated files
    print("\nGenerated configuration files:")
    for command_key in HANDLE_DEFAULTS_REGISTRY:
        file_path = get_plugin_config_file(f"{command_key}.json5")
        print(f"\n{command_key}.json5:")
        print(f"  Path: {file_path}")

        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            config_dict = json5.loads(content)

            # Validate
            is_valid = manager.validate_config(command_key, config_dict)
            print(f"  Schema validation: {'✓ PASSED' if is_valid else '✗ FAILED'}")

            # Display content summary
            print("  Content:")
            print(f"    - $schema: {config_dict.get('$schema')}")
            print(f"    - enabled: {config_dict.get('enabled')}")
            print(f"    - defaults: {config_dict.get('defaults')}")
            print(f"    - policies: {config_dict.get('policies')}")
        else:
            print("  ✗ File does not exist")

    # Verify schema file
    schema_path = config_dir / HANDLE_CONFIG_SCHEMA_BASENAME
    print(f"\nSchema file: {schema_path}")
    print(f"  Exists: {'✓' if schema_path.exists() else '✗'}")


if __name__ == "__main__":
    generate_handle_configs()
