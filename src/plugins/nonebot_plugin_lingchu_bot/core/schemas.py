"""JSON Schema resources for runtime TOML files.

This module is the single source of truth for the JSON Schema definitions
that describe ``config.toml`` and ``bot_state.toml``. The schema texts
are stored as plain Python string literals and written to the
``nonebot_plugin_localstore``-managed ``config_dir`` and ``data_dir`` at
startup by :func:`install_schemas`, so that the schema files live next
to the runtime TOML files they describe. Editors that resolve
``$schema`` basenames will then locate the sibling schema in the same
localstore directory.

Paths are resolved exclusively through ``get_plugin_config_dir`` and
``get_plugin_data_dir`` — no hard-coded relative or absolute paths are
permitted in this module, and no ``importlib.resources`` / wheel data
indirection is used.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Final

import aiofiles
import aiofiles.os
from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_dir, get_plugin_data_dir

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_SCHEMA_BASENAME: Final = "config.schema.json"
BOT_STATE_SCHEMA_BASENAME: Final = "bot_state.schema.json"
MENU_SCHEMA_BASENAME: Final = "menu.schema.json"
HANDLE_CONFIG_SCHEMA_BASENAME: Final = "handle_config.schema.json"
LLM_SCHEMA_BASENAME: Final = "llm.schema.json"

CONFIG_SCHEMA_TEXT: Final = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Lingchu Bot Runtime Config",
  "description": "Lightweight runtime settings for the Lingchu Bot plugin. Values here are low-priority defaults; NoneBot global_config, environment variables and dotenv files override them at runtime.",
  "type": "object",
  "additionalProperties": true,
  "properties": {
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
      "type": "string",
      "description": "Optional OpenAI-compatible API base URL passed to the selected LLM provider."
    },
    "ai_timeout": {
      "type": "number",
      "exclusiveMinimum": 0,
      "description": "LLM request timeout in seconds."
    },
    "ai_api_key": {
      "type": "string",
      "description": "LLM provider API key. Prefer setting via the LINGCHU_AI_API_KEY environment variable over writing it into the TOML config file."
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
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": {
          "oneOf": [
            { "type": "string" },
            { "type": "integer" }
          ]
        }
      },
      "description": "Mapping of logical lingchu user id to per-platform account id (string or integer)."
    },
    "lingchu_adapter": {
      "oneOf": [
        { "type": "string" },
        {
          "type": "array",
          "items": { "type": "string" }
        }
      ],
      "description": "Adapter selector for the lingchu ecosystem. Accepts a single id or a list of ids; omit the key to fall back to all registered adapters."
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
  "required": ["enabled"],
  "properties": {
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
LLM_SCHEMA_TEXT: Final = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Lingchu Bot LLM Configuration",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "default_profile": {"type": "string"},
    "profiles": {"type": "object", "propertyNames": {"type": "string", "minLength": 1}, "additionalProperties": {"type": "object", "additionalProperties": false, "required": ["model"], "properties": {
      "backend": {"type": "string", "enum": ["litellm", "openai"]}, "model": {"type": "string", "minLength": 1},
      "base_url": {"type": "string", "format": "uri"}, "api_key_env": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
      "organization": {"type": "string"}, "project": {"type": "string"}, "timeout": {"type": "number", "exclusiveMinimum": 0},
      "max_retries": {"type": "integer", "minimum": 0, "maximum": 20}, "default_headers": {"type": "object", "additionalProperties": {"type": "string"}},
      "default_query": {"type": "object", "maxProperties": 100, "description": "Query parameters passed to the provider."}, "provider_options": {"type": "object", "maxProperties": 100, "description": "Provider-specific options; unknown keys are forwarded."}, "litellm_generation": {"type": "string", "enum": ["responses", "chat"]},
      "allow_private_network": {"type": "boolean"}, "allow_credentials_to_custom_base_url": {"type": "boolean"}
    }}},
    "router": {"type": "object", "additionalProperties": false, "description": "LiteLLM router settings. Provider-specific extensions belong in extensions.", "properties": {
      "enabled": {"type": "boolean"}, "strategy": {"type": "string"}, "num_retries": {"type": "integer", "minimum": 0}, "timeout": {"type": "number", "exclusiveMinimum": 0}, "extensions": {"type": "object", "additionalProperties": true}
    }},
    "observability": {"type": "object", "additionalProperties": false, "description": "Safe allowlisted stable-call logging.", "properties": {
      "enabled": {"type": "boolean", "default": true}
    }}
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
    """Write JSON Schema files to localstore dirs; idempotent, propagates I/O errors."""
    config_dir: Path = get_plugin_config_dir()
    config_path: Path = config_dir / CONFIG_SCHEMA_BASENAME
    menu_path: Path = config_dir / MENU_SCHEMA_BASENAME
    handle_config_path: Path = config_dir / HANDLE_CONFIG_SCHEMA_BASENAME
    llm_path: Path = config_dir / LLM_SCHEMA_BASENAME
    data_path: Path = get_plugin_data_dir() / BOT_STATE_SCHEMA_BASENAME

    await aiofiles.os.makedirs(config_path.parent, exist_ok=True)
    await aiofiles.os.makedirs(data_path.parent, exist_ok=True)

    async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
        await f.write(CONFIG_SCHEMA_TEXT)
    async with aiofiles.open(menu_path, "w", encoding="utf-8") as f:
        await f.write(MENU_SCHEMA_TEXT)
    async with aiofiles.open(handle_config_path, "w", encoding="utf-8") as f:
        await f.write(HANDLE_CONFIG_SCHEMA_TEXT)
    async with aiofiles.open(llm_path, "w", encoding="utf-8") as f:
        await f.write(LLM_SCHEMA_TEXT)
    async with aiofiles.open(data_path, "w", encoding="utf-8") as f:
        await f.write(BOT_STATE_SCHEMA_TEXT)

    logger.debug(
        "Lingchu configuration schemas installed: "
        f"config={config_path}, menu={menu_path}, handle={handle_config_path}, state={data_path}"
    )
