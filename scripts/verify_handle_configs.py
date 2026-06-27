"""Verify handle configuration files for Lingchu Bot.

This script validates that the generated handle configuration JSON5 files
pass schema validation and contain the expected content.
"""

import json
import sys
from pathlib import Path

import json5
import jsonschema

# Project root
project_root = Path(__file__).parent.parent
config_dir = project_root / "config" / "nonebot_plugin_lingchu_bot"

# Expected defaults for each handle
EXPECTED_CONFIGS = {
    "kick_member": {
        "enabled": True,
        "defaults": {"require_reason": False, "audit_level": "low"},
        "policies": {},
    },
    "protect_member": {
        "enabled": True,
        "defaults": {"whitelist_scope": "group"},
        "policies": {},
    },
    "block_member": {
        "enabled": True,
        "defaults": {"block_duration": None, "default_reason": "违反群规"},
        "policies": {},
    },
    "member_mute": {
        "enabled": True,
        "defaults": {"mute_duration": 300, "default_reason": "管理员操作"},
        "policies": {},
    },
    "recall_message": {
        "enabled": True,
        "defaults": {"default_count": 10},
        "policies": {},
    },
}


def verify_handle_configs() -> bool:
    """Verify all handle configuration files."""
    print("Verifying handle configuration files...")
    print(f"Config directory: {config_dir}\n")

    # Load schema
    schema_path = config_dir / "handle_config.schema.json5"
    if not schema_path.exists():
        print(f"✗ Schema file not found: {schema_path}")
        return False

    print(f"Schema file: {schema_path}")
    schema_text = schema_path.read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    print("✓ Schema loaded successfully\n")

    # Verify each handle config
    all_valid = True
    for command_key, expected in EXPECTED_CONFIGS.items():
        file_path = config_dir / f"{command_key}.json5"
        print(f"{command_key}.json5:")
        print(f"  Path: {file_path}")

        if not file_path.exists():
            print("  ✗ File does not exist\n")
            all_valid = False
            continue

        # Parse JSON5
        try:
            content = file_path.read_text(encoding="utf-8")
            config_dict = json5.loads(content)
            print("  ✓ JSON5 parseable")
        except Exception as e:
            print(f"  ✗ JSON5 parse failed: {e}\n")
            all_valid = False
            continue

        # Verify $schema field
        if config_dict.get("$schema") != "handle_config.schema.json5":
            print(f"  ✗ Invalid $schema: {config_dict.get('$schema')}\n")
            all_valid = False
            continue
        print("  ✓ $schema: handle_config.schema.json5")

        # Validate against schema
        try:
            jsonschema.validate(config_dict, schema)
            print("  ✓ Schema validation passed")
        except jsonschema.ValidationError as e:
            print(f"  ✗ Schema validation failed: {e.message}\n")
            all_valid = False
            continue

        # Verify content matches expected
        if config_dict.get("enabled") != expected["enabled"]:
            print(
                f"  ✗ enabled mismatch: {config_dict.get('enabled')} != {expected['enabled']}\n"
            )
            all_valid = False
            continue
        print(f"  ✓ enabled: {config_dict.get('enabled')}")

        if config_dict.get("defaults") != expected["defaults"]:
            print(
                f"  ✗ defaults mismatch:\n    {config_dict.get('defaults')}\n    !=\n    {expected['defaults']}\n"
            )
            all_valid = False
            continue
        print(f"  ✓ defaults: {config_dict.get('defaults')}")

        if config_dict.get("policies") != expected["policies"]:
            print(
                f"  ✗ policies mismatch: {config_dict.get('policies')} != {expected['policies']}\n"
            )
            all_valid = False
            continue
        print(f"  ✓ policies: {config_dict.get('policies')}")

        print("  ✓ All checks passed\n")

    # Summary
    print("=" * 60)
    if all_valid:
        print("✓ ALL HANDLE CONFIGURATIONS VERIFIED SUCCESSFULLY")
        return True
    print("✗ SOME HANDLE CONFIGURATIONS FAILED VERIFICATION")
    return False


if __name__ == "__main__":
    success = verify_handle_configs()
    sys.exit(0 if success else 1)
