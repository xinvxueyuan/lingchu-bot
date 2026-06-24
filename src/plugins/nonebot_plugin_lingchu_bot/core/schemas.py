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

from typing import TYPE_CHECKING, Final

from nonebot import logger
from nonebot_plugin_localstore import get_plugin_config_dir, get_plugin_data_dir

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_SCHEMA_BASENAME: Final = "config.schema.json5"
BOT_STATE_SCHEMA_BASENAME: Final = "bot_state.schema.json5"

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


def install_schemas() -> None:
    """Write JSON5 schema files to the localstore config / data directories.

    The two schemas are placed as siblings of ``config.json5`` and
    ``bot_state.json5`` respectively, so the ``$schema`` basename injected
    by :mod:`core.runtime_config` and :mod:`core.bot_state` resolves to
    a real file managed by ``nonebot_plugin_localstore``. Calling this
    function multiple times is safe: the writes are idempotent.
    """
    config_path: Path = get_plugin_config_dir() / CONFIG_SCHEMA_BASENAME
    data_path: Path = get_plugin_data_dir() / BOT_STATE_SCHEMA_BASENAME

    config_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.parent.mkdir(parents=True, exist_ok=True)

    config_path.write_text(CONFIG_SCHEMA_TEXT, encoding="utf-8")
    data_path.write_text(BOT_STATE_SCHEMA_TEXT, encoding="utf-8")

    logger.debug(
        f"Lingchu JSON5 schemas installed: config={config_path}, state={data_path}"
    )
