"""Child-owned NovelAI configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final, Literal

from nonebot import get_driver, require
from nonebot.compat import type_validate_python
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ....database.json5_store import (
    ensure_json5_dict_file_sync,
    load_json5_dict_sync,
)
from ...runtime_config import runtime_config
from ..contracts import LLMOptions

CONFIG_FILENAME: Final = "novelai_image.json5"
SCHEMA_FILENAME: Final = "novelai_image.schema.json5"


class NovelAIConfig(BaseModel):
    enabled: bool = True
    token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINGCHU_NOVELAI_TOKEN", "token"),
    )
    base_url: str = Field(
        default="https://image.novelai.net",
        validation_alias=AliasChoices("LINGCHU_NOVELAI_BASE_URL", "base_url"),
    )
    model: str = Field(
        default="nai-diffusion-4-5-full",
        min_length=1,
        validation_alias=AliasChoices("LINGCHU_NOVELAI_MODEL", "model"),
    )
    timeout: float = Field(
        default=120.0,
        gt=0,
        validation_alias=AliasChoices("LINGCHU_NOVELAI_TIMEOUT", "timeout"),
    )
    width: int = Field(default=832, ge=64, le=2048)
    height: int = Field(default=1216, ge=64, le=2048)
    steps: int = Field(default=28, ge=1, le=50)
    scale: float = Field(default=5.0, gt=0, le=20)
    sampler: str = "k_euler_ancestral"
    negative_prompt: str = (
        "lowres, bad anatomy, bad hands, text, watermark, worst quality"
    )
    prompt_llm_provider: Literal["litellm", "openai"] | None = None
    prompt_llm_model: str | None = Field(default=None, min_length=1)
    prompt_llm_base_url: str | None = None
    prompt_llm_api_key: str | None = None
    prompt_llm_timeout: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(extra="ignore")


def novelai_config_defaults() -> dict[str, Any]:
    return {
        "$schema": SCHEMA_FILENAME,
        **NovelAIConfig().model_dump(mode="json"),
    }


def _config_file(name: str) -> Path:
    return get_plugin_config_file(name)


def ensure_novelai_config_files() -> None:
    ensure_json5_dict_file_sync(
        _config_file(CONFIG_FILENAME),
        novelai_config_defaults(),
    )
    ensure_json5_dict_file_sync(
        _config_file(SCHEMA_FILENAME),
        NovelAIConfig.model_json_schema(mode="serialization"),
    )


def get_novelai_config(config_file: str | Path | None = None) -> NovelAIConfig:
    path = (
        Path(config_file) if config_file is not None else _config_file(CONFIG_FILENAME)
    )
    raw = novelai_config_defaults() | load_json5_dict_sync(path)
    try:
        global_config = get_driver().config
    except ValueError:
        global_config = None
    for field in NovelAIConfig.model_fields:
        env_key = f"LINGCHU_NOVELAI_{field.upper()}"
        value = os.environ.get(env_key)
        if value is None and global_config is not None:
            value = getattr(global_config, env_key.lower(), None)
        if value not in (None, ""):
            raw[field] = value
    return type_validate_python(NovelAIConfig, raw)


def resolve_prompt_llm_options(config: NovelAIConfig) -> LLMOptions:
    return LLMOptions(
        provider=config.prompt_llm_provider or runtime_config.ai_provider,
        model=config.prompt_llm_model or runtime_config.ai_model,
        base_url=config.prompt_llm_base_url or runtime_config.ai_base_url,
        api_key=config.prompt_llm_api_key or runtime_config.ai_api_key,
        timeout=config.prompt_llm_timeout or runtime_config.ai_timeout,
    )
