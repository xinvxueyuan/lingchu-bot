"""Child-owned LLM chat configuration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from pathlib import Path

from nonebot import require
from nonebot.compat import type_validate_python
from pydantic import BaseModel, ConfigDict

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ..contracts import ensure_subplugin_config_file, load_subplugin_config

CONFIG_FILENAME: Final = "llm_chat.toml"
SCHEMA_FILENAME: Final = "llm_chat.schema.json"


class ChatConfig(BaseModel):
    enabled: bool = True
    system_prompt: str = "你是一个友好的群聊助手。"

    model_config = ConfigDict(extra="ignore")


def chat_config_defaults() -> dict[str, Any]:
    return ChatConfig().model_dump(mode="json")


def chat_config_schema() -> dict[str, Any]:
    return ChatConfig.model_json_schema(mode="serialization")


def _config_file(name: str) -> Path:
    return get_plugin_config_file(name)


def ensure_chat_config_files() -> None:
    ensure_subplugin_config_file(
        CONFIG_FILENAME,
        chat_config_defaults(),
        schema_basename=SCHEMA_FILENAME,
    )
    schema_path = _config_file(SCHEMA_FILENAME)
    if not schema_path.exists():
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = schema_path.with_suffix(".tmp.json")
        temp_path.write_text(
            json.dumps(
                chat_config_schema(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp_path.replace(schema_path)


def get_chat_config() -> ChatConfig:
    raw = chat_config_defaults() | load_subplugin_config(CONFIG_FILENAME)
    return type_validate_python(ChatConfig, raw)
