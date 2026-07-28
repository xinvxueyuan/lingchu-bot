"""JSON Schema resources for runtime TOML files.

This module is the single source of truth for the JSON Schema basenames
that describe ``config.toml``, ``bot_state.toml``, ``menu.toml``,
``<command_key>.toml`` and ``llm.toml``. The schema files are written to
the ``nonebot_plugin_localstore``-managed ``config_dir`` and ``data_dir``
at startup by :func:`install_schemas`, so that the schema files live
next to the runtime TOML files they describe. Editors that resolve
``$schema`` basenames will then locate the sibling schema in the same
localstore directory.

Schemas backed by a pydantic ``BaseModel`` are generated at write time
via ``model_json_schema()``; schemas without a pydantic model
(:data:`MENU_SCHEMA_TEXT`, :data:`LLM_SCHEMA_TEXT`) remain as plain
Python string literals.

Paths are resolved exclusively through ``get_plugin_config_dir`` and
``get_plugin_data_dir`` — no hard-coded relative or absolute paths are
permitted in this module, and no ``importlib.resources`` / wheel data
indirection is used.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Final

from _lingchu_bot_contracts import DeploymentSettings
from nonebot import logger, require
from pydantic import BaseModel, ConfigDict, Field

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_dir, get_plugin_data_dir

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_SCHEMA_BASENAME: Final = "config.schema.json"
BOT_STATE_SCHEMA_BASENAME: Final = "bot_state.schema.json"
MENU_SCHEMA_BASENAME: Final = "menu.schema.json"
HANDLE_CONFIG_SCHEMA_BASENAME: Final = "handle_config.schema.json"
LLM_SCHEMA_BASENAME: Final = "llm.schema.json"

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

LLM_SCHEMA_TEXT: Final = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Lingchu Bot LLM Configuration",
  "description": "Configures the in-process Pydantic AI agent. Legacy eve/profiles/router sections are ignored.",
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "pydantic-ai": {"type": "object", "additionalProperties": false, "description": "In-process Pydantic AI agent configuration.", "required": ["model"], "properties": {
      "model": {"type": "string", "pattern": "^[\\\\w.-]+:[\\\\w./-]+$", "minLength": 1, "description": "Pydantic AI model string, e.g. \\"openai:gpt-5.2\\"."},
      "api_key_env": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$", "description": "Optional environment variable name holding the provider API key."},
      "base_url": {"type": "string", "description": "Optional custom provider base URL."},
      "timeout": {"type": "number", "exclusiveMinimum": 0, "default": 60}
    }},
    "mcp": {"type": "object", "additionalProperties": false, "description": "MCP Agent runtime toggles consumed by the Pydantic AI MCP capability.", "properties": {
      "enabled": {"type": "boolean", "default": false},
      "review_profile": {"type": "string", "default": "default"},
      "max_tool_rounds": {"type": "integer", "minimum": 1, "maximum": 5, "default": 5},
      "servers": {"type": "object", "description": "MCP server definitions keyed by stable name; each entry is handed to a Pydantic AI MCPToolset.", "additionalProperties": {"type": "object", "additionalProperties": false, "required": ["transport"], "properties": {
        "transport": {"type": "string", "enum": ["stdio", "streamable_http"]},
        "command": {"type": "string", "description": "Required when transport == \\"stdio\\"."},
        "args": {"type": "array", "items": {"type": "string"}},
        "url": {"type": "string", "description": "Required when transport == \\"streamable_http\\"."},
        "headers_env": {"type": "string", "description": "Optional env var name holding a JSON headers dict."},
        "allow_private_network": {"type": "boolean", "default": false}
      }}}
    }},
    "observability": {"type": "object", "additionalProperties": false, "description": "Safe allowlisted stable-call logging.", "properties": {
      "enabled": {"type": "boolean", "default": true}
    }}
  }
}
"""


class _HandleConfigSchemaModel(BaseModel):
    """Generic handle config schema model.

    Used only to generate the generic ``handle_config.schema.json``.
    Each handle's actual config is validated by its own pydantic model
    registered in ``HANDLE_DEFAULTS_REGISTRY``; this model captures the
    shared ``enabled`` / ``defaults`` / ``policies`` shape.
    """

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)


def _write_schema(path: Path, schema: dict[str, Any]) -> None:
    """Write a pydantic-generated JSON schema to disk with indentation."""
    content = json.dumps(schema, indent=2, ensure_ascii=False)
    path.write_text(content, encoding="utf-8")


def _write_schema_text(path: Path, schema_text: str) -> None:
    """Write a hand-authored JSON schema string to disk verbatim."""
    path.write_text(schema_text, encoding="utf-8")


def _ensure_schema_dirs(config_dir: Path, data_dir: Path) -> None:
    """Ensure schema target directories exist."""
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)


async def install_schemas() -> None:
    """Write JSON Schema files to localstore dirs; idempotent, propagates I/O errors.

    Schemas backed by a pydantic ``BaseModel`` are generated via
    ``model_json_schema()``; schemas without a pydantic model
    (:data:`MENU_SCHEMA_TEXT`, :data:`LLM_SCHEMA_TEXT`) are written as
    hand-authored string literals.
    """
    config_dir: Path = get_plugin_config_dir()
    data_dir: Path = get_plugin_data_dir()

    _ensure_schema_dirs(config_dir, data_dir)

    # CONFIG_SCHEMA from the import-safe deployment settings contract.
    _write_schema(
        config_dir / CONFIG_SCHEMA_BASENAME,
        DeploymentSettings.model_json_schema(),
    )

    # BOT_STATE_SCHEMA from BotStateFile (defined in bot_state.py; local import).
    from .bot_state import BotStateFile

    _write_schema(
        data_dir / BOT_STATE_SCHEMA_BASENAME,
        BotStateFile.model_json_schema(),
    )

    # HANDLE_CONFIG_SCHEMA from the generic handle config shape model.
    _write_schema(
        config_dir / HANDLE_CONFIG_SCHEMA_BASENAME,
        _HandleConfigSchemaModel.model_json_schema(),
    )

    # MENU_SCHEMA and LLM_SCHEMA: no public pydantic model exists, so the
    # hand-authored JSON Schema string literals are written verbatim.
    _write_schema_text(config_dir / MENU_SCHEMA_BASENAME, MENU_SCHEMA_TEXT)
    _write_schema_text(config_dir / LLM_SCHEMA_BASENAME, LLM_SCHEMA_TEXT)

    logger.debug("Lingchu configuration schemas installed")
