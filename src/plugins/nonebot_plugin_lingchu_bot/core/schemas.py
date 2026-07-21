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

import aiofiles
import aiofiles.os
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
    }},
    "mcp": {"type": "object", "additionalProperties": false, "description": "Explicit reviewed MCP Agent runtime. Ordinary LLM calls remain tool-free.", "properties": {
      "enabled": {"type": "boolean", "default": false},
      "review_profile": {"type": "string", "minLength": 1},
      "max_tool_rounds": {"type": "integer", "minimum": 1, "maximum": 5, "default": 5},
      "max_parallel_tools": {"type": "integer", "minimum": 1, "maximum": 4, "default": 4},
      "tool_timeout": {"type": "number", "exclusiveMinimum": 0, "maximum": 300, "default": 15},
      "result_limit_bytes": {"type": "integer", "minimum": 1024, "maximum": 1048576, "default": 65536},
      "request_timeout": {"type": "number", "exclusiveMinimum": 0, "maximum": 900, "default": 90},
      "servers": {"type": "array", "items": {"type": "object", "additionalProperties": false, "required": ["name", "transport"], "properties": {
        "name": {"type": "string", "maxLength": 64, "pattern": "^[a-z0-9][a-z0-9_-]*$"},
        "transport": {"type": "string", "enum": ["stdio", "streamable_http"]},
        "command": {"type": "string", "minLength": 1},
        "args": {"type": "array", "items": {"type": "string"}},
        "url": {"type": "string", "format": "uri"},
        "headers_env": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
        "allow_private_network": {"type": "boolean", "default": false}
      }} }
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


async def _write_schema(path: Path, schema: dict[str, Any]) -> None:
    """Write a pydantic-generated JSON schema to disk with indentation."""
    content = json.dumps(schema, indent=2, ensure_ascii=False)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)


async def _write_schema_text(path: Path, schema_text: str) -> None:
    """Write a hand-authored JSON schema string to disk verbatim."""
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(schema_text)


async def install_schemas() -> None:
    """Write JSON Schema files to localstore dirs; idempotent, propagates I/O errors.

    Schemas backed by a pydantic ``BaseModel`` are generated via
    ``model_json_schema()``; schemas without a pydantic model
    (:data:`MENU_SCHEMA_TEXT`, :data:`LLM_SCHEMA_TEXT`) are written as
    hand-authored string literals.
    """
    config_dir: Path = get_plugin_config_dir()
    data_dir: Path = get_plugin_data_dir()

    await aiofiles.os.makedirs(config_dir, exist_ok=True)
    await aiofiles.os.makedirs(data_dir, exist_ok=True)

    # CONFIG_SCHEMA from Config (local import to avoid circular dependency).
    from .config import Config

    await _write_schema(
        config_dir / CONFIG_SCHEMA_BASENAME,
        Config.model_json_schema(),
    )

    # BOT_STATE_SCHEMA from BotStateFile (defined in bot_state.py; local import).
    from .bot_state import BotStateFile

    await _write_schema(
        data_dir / BOT_STATE_SCHEMA_BASENAME,
        BotStateFile.model_json_schema(),
    )

    # HANDLE_CONFIG_SCHEMA from the generic handle config shape model.
    await _write_schema(
        config_dir / HANDLE_CONFIG_SCHEMA_BASENAME,
        _HandleConfigSchemaModel.model_json_schema(),
    )

    # MENU_SCHEMA and LLM_SCHEMA: no public pydantic model exists, so the
    # hand-authored JSON Schema string literals are written verbatim.
    await _write_schema_text(config_dir / MENU_SCHEMA_BASENAME, MENU_SCHEMA_TEXT)
    await _write_schema_text(config_dir / LLM_SCHEMA_BASENAME, LLM_SCHEMA_TEXT)

    logger.debug("Lingchu configuration schemas installed")
