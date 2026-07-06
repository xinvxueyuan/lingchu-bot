"""JSON5 Schema resources for runtime JSON5 files.

This module is the single source of truth for the JSON Schema definitions
that describe ``config.json5`` and ``bot_state.json5``. The schema texts
are stored as plain Python string literals and written to the
``nonebot_plugin_localstore``-managed ``config_dir`` and ``data_dir`` at
startup by :func:`install_schemas`, so that the schema files live next
to the runtime JSON5 files they describe. Editors that resolve
``$schema`` basenames will then locate the sibling schema in the same
localstore directory.

Paths are resolved exclusively through ``get_plugin_config_dir`` and
``get_plugin_data_dir`` — no hard-coded relative or absolute paths are
permitted in this module, and no ``importlib.resources`` / wheel data
indirection is used.
"""

# ruff: noqa: E501
# E501 disabled: the embedded JSON Schema strings intentionally use long
# description lines for human readability inside editors; line wrapping
# inside a triple-quoted string would change the on-disk content.

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import aiofiles.os
from nonebot import logger
from nonebot_plugin_localstore import get_plugin_config_dir, get_plugin_data_dir

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_SCHEMA_BASENAME: Final = "config.schema.json5"
BOT_STATE_SCHEMA_BASENAME: Final = "bot_state.schema.json5"
MENU_SCHEMA_BASENAME: Final = "menu.schema.json5"
HANDLE_CONFIG_SCHEMA_BASENAME: Final = "handle_config.schema.json5"

CONFIG_SCHEMA_TEXT: Final = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Lingchu Bot Runtime Config",
  "description": "Lightweight runtime settings for the Lingchu Bot plugin. Values here are low-priority defaults; NoneBot global_config, environment variables and dotenv files override them at runtime.",
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "$schema": {
      "type": "string",
      "description": "Editor hint pointing to the sibling schema file in the same directory."
    },
    "superuser_key": {
      "type": "string",
      "description": "Runtime superuser key used by permission checks."
    },
    "message_store_enabled": {
      "type": "boolean",
      "description": "Enable message-store hooks."
    },
    "message_store_retention_days": {
      "type": "integer",
      "minimum": 0,
      "description": "How many days of messages to keep in the store."
    },
    "message_store_summary_limit": {
      "type": "integer",
      "minimum": 0,
      "description": "Maximum number of messages summarised in a single request."
    },
    "message_store_record_api_calls": {
      "type": "boolean",
      "description": "Record adapter API calls into the message store."
    },
    "message_store_cleanup_enabled": {
      "type": "boolean",
      "description": "Run periodic cleanup against the message store."
    },
    "ai_provider": {
      "type": "string",
      "enum": ["litellm", "openai"],
      "description": "LLM SDK backend. Use litellm by default; switch to openai as a direct SDK fallback."
    },
    "ai_model": {
      "type": "string",
      "description": "Default chat completion model passed to the selected LLM provider."
    },
    "ai_base_url": {
      "oneOf": [
        { "type": "null" },
        { "type": "string" }
      ],
      "description": "Optional OpenAI-compatible API base URL passed to the selected LLM provider."
    },
    "ai_timeout": {
      "type": "number",
      "exclusiveMinimum": 0,
      "description": "LLM request timeout in seconds."
    },
    "ai_api_key": {
      "oneOf": [
        { "type": "null" },
        { "type": "string" }
      ],
      "description": "LLM provider API key. Prefer setting via the AI_API_KEY environment variable over writing it into the JSON5 config file."
    },
    "recall_message_default_count": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "description": "Default number of messages to recall when the user does not specify a count."
    },
    "permission_platform_runtime_passthrough": {
      "oneOf": [
        { "type": "boolean" },
        {
          "type": "object",
          "additionalProperties": { "type": "boolean" }
        }
      ],
      "description": "Toggle permission-platform runtime passthrough globally or per platform id."
    },
    "command_trigger_overrides": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": true
      },
      "description": "Per-command trigger overrides keyed by command name."
    },
    "menu_page_trigger_overrides": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": true
      },
      "description": "Per-menu-page trigger overrides keyed by menu page id."
    },
    "protected_subject_feature_keys": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Command feature keys covered by the handle whitelist gate. Targets in protected subject policy cannot be managed by these commands unless the operator is in the repository-backed SUPERUSERS group."
    },
    "lingchu_superusers": {
      "oneOf": [
        { "type": "null" },
        {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "additionalProperties": {
              "oneOf": [
                { "type": "string" },
                { "type": "integer" }
              ]
            }
          }
        }
      ],
      "description": "Mapping of logical lingchu user id to per-platform account id (string or integer)."
    },
    "lingchu_adapter": {
      "oneOf": [
        { "type": "null" },
        { "type": "string" },
        {
          "type": "array",
          "items": { "type": "string" }
        }
      ],
      "description": "Adapter selector for the lingchu ecosystem. Accepts a single id, a list of ids, or null to fall back to all registered adapters."
    }
  }
}
"""

BOT_STATE_SCHEMA_TEXT: Final = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Lingchu Bot Runtime State",
  "description": "Two-tier bot state persisted by the Lingchu Bot plugin. Global flags apply to every platform; per-platform entries override the global values.",
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "$schema": {
      "type": "string",
      "description": "Editor hint pointing to the sibling schema file in the same directory."
    },
    "global": {
      "type": "object",
      "description": "Global state shared by every platform.",
      "additionalProperties": false,
      "properties": {
        "handle_active": {
          "type": "boolean",
          "description": "When false, all platforms are gated off regardless of per-platform overrides."
        },
        "silent_mode": {
          "type": "boolean",
          "description": "When true, every platform is silenced regardless of per-platform overrides."
        }
      }
    },
    "platforms": {
      "type": "object",
      "description": "Per-platform overrides keyed by platform id (e.g. \"qq\", \"telegram\").",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "handle_active": { "type": "boolean" },
          "silent_mode": { "type": "boolean" }
        }
      }
    }
  }
}
"""

MENU_SCHEMA_TEXT: Final = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Lingchu Bot Menu Config",
  "description": "Editable menu labels, page order, and command help text for the Lingchu Bot plugin. Runtime availability and command identity stay code-owned.",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "pages"],
  "properties": {
    "$schema": {
      "type": "string",
      "description": "Editor hint pointing to the sibling schema file in the same directory."
    },
    "version": {
      "type": "integer",
      "description": "Menu config format version."
    },
    "pages": {
      "type": "array",
      "items": { "$ref": "#/definitions/page" }
    }
  },
  "definitions": {
    "localizedText": {
      "type": "object",
      "additionalProperties": false,
      "required": ["zh_CN", "en_US"],
      "properties": {
        "zh_CN": { "type": "string" },
        "en_US": { "type": "string" }
      }
    },
    "menuItem": {
      "type": "object",
      "additionalProperties": false,
      "required": ["command_key", "summary", "usage"],
      "properties": {
        "command_key": { "type": "string" },
        "summary": { "$ref": "#/definitions/localizedText" },
        "usage": { "$ref": "#/definitions/localizedText" }
      }
    },
    "page": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "title"],
      "properties": {
        "id": { "type": "string" },
        "title": { "$ref": "#/definitions/localizedText" },
        "command": { "$ref": "#/definitions/localizedText" },
        "items": {
          "type": "array",
          "items": { "$ref": "#/definitions/menuItem" }
        },
        "children": {
          "type": "array",
          "items": { "$ref": "#/definitions/page" }
        }
      }
    }
  }
}
"""

HANDLE_CONFIG_SCHEMA_TEXT: Final = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Lingchu Bot Handle Config",
  "description": "Standard handle-level configuration schema",
  "type": "object",
  "required": ["$schema", "enabled"],
  "properties": {
    "$schema": {
      "type": "string",
      "description": "Editor hint pointing to the sibling schema file in the same directory."
    },
    "enabled": {
      "type": "boolean",
      "default": true,
      "description": "Whether this handle is enabled."
    },
    "defaults": {
      "type": "object",
      "additionalProperties": true,
      "description": "Default values for handle-specific configuration fields."
    },
    "policies": {
      "type": "object",
      "additionalProperties": true,
      "description": "Policy configuration for this handle."
    }
  }
}
"""


def generate_handle_schema(command_key: str, defaults_fields: dict[str, Any]) -> str:
    """Generate a specialized handle configuration schema based on the generic template.

    This function creates a JSON Schema for a specific handle by extending the
    base ``HANDLE_CONFIG_SCHEMA_TEXT`` with custom fields in the ``defaults`` object.

    Args:
        command_key: The unique identifier for the command/handle.
        defaults_fields: A dictionary mapping field names to their JSON Schema definitions.
            Each entry will be added as a property in the ``defaults`` object.

    Returns:
        A JSON string representing the specialized schema for this handle.

    Example:
        >>> schema = generate_handle_schema("recall", {
        ...     "count": {"type": "integer", "minimum": 1, "maximum": 100},
        ...     "silent": {"type": "boolean", "default": false}
        ... })
    """
    schema_obj = json.loads(HANDLE_CONFIG_SCHEMA_TEXT)

    # Update title to reflect the specific handle
    schema_obj["title"] = f"Lingchu Bot Handle Config - {command_key}"
    schema_obj["description"] = f"Configuration schema for the {command_key} handle"

    # Add custom fields to defaults properties
    if defaults_fields:
        schema_obj["properties"]["defaults"]["properties"] = defaults_fields

    return json.dumps(schema_obj, indent=2, ensure_ascii=False)


async def install_schemas() -> None:
    """Write JSON5 schema files to localstore dirs; idempotent, propagates I/O errors."""
    config_dir: Path = get_plugin_config_dir()
    config_path: Path = config_dir / CONFIG_SCHEMA_BASENAME
    menu_path: Path = config_dir / MENU_SCHEMA_BASENAME
    handle_config_path: Path = config_dir / HANDLE_CONFIG_SCHEMA_BASENAME
    data_path: Path = get_plugin_data_dir() / BOT_STATE_SCHEMA_BASENAME

    await aiofiles.os.makedirs(config_path.parent, exist_ok=True)
    await aiofiles.os.makedirs(data_path.parent, exist_ok=True)

    async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
        await f.write(CONFIG_SCHEMA_TEXT)
    async with aiofiles.open(menu_path, "w", encoding="utf-8") as f:
        await f.write(MENU_SCHEMA_TEXT)
    async with aiofiles.open(handle_config_path, "w", encoding="utf-8") as f:
        await f.write(HANDLE_CONFIG_SCHEMA_TEXT)
    async with aiofiles.open(data_path, "w", encoding="utf-8") as f:
        await f.write(BOT_STATE_SCHEMA_TEXT)

    logger.debug(
        "Lingchu JSON5 schemas installed: "
        f"config={config_path}, menu={menu_path}, handle={handle_config_path}, state={data_path}"
    )
