"""Child-owned NovelAI configuration."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, Final

from nonebot import get_driver, require
from nonebot.compat import type_validate_python
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ..contracts import ensure_subplugin_config_file, load_subplugin_config

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_FILENAME: Final = "novelai_image.toml"
SCHEMA_FILENAME: Final = "novelai_image.schema.json"


class NovelAIConfig(BaseModel):
    enabled: bool = True
    token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINGCHU_NOVELAI_TOKEN", "token"),
    )
    username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINGCHU_NOVELAI_USERNAME", "username"),
    )
    password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINGCHU_NOVELAI_PASSWORD", "password"),
    )
    base_url: str = Field(
        default="https://image.novelai.net",
        validation_alias=AliasChoices("LINGCHU_NOVELAI_BASE_URL", "base_url"),
    )
    account_base_url: str = Field(
        default="https://api.novelai.net",
        validation_alias=AliasChoices(
            "LINGCHU_NOVELAI_ACCOUNT_BASE_URL",
            "account_base_url",
        ),
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
    n_samples: int = Field(default=1, ge=1, le=8)
    steps: int = Field(default=28, ge=1, le=50)
    scale: float = Field(default=5.0, gt=0, le=20)
    sampler: str = "k_euler_ancestral"
    negative_prompt: str = (
        "lowres, bad anatomy, bad hands, text, watermark, worst quality"
    )
    quality: bool = True
    uc_preset: int = Field(default=0, ge=0, le=3)
    noise_schedule: str = "karras"
    cfg_rescale: float = Field(default=0.0, ge=0, le=1)
    dynamic_thresholding: bool = False
    auto_smea: bool = False
    prefer_brownian: bool = True
    vibe_cache_entries: int = Field(default=64, ge=1, le=1024)
    image_download_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
        le=64 * 1024 * 1024,
    )
    tipo_enabled: bool = True
    tipo_base_url: str = "http://127.0.0.1:8081/v1"
    tipo_model: str = Field(default="tipo-500m-ft", min_length=1)
    tipo_api_key: str | None = None
    tipo_timeout: float = Field(default=30.0, gt=0)
    tipo_max_tokens: int = Field(default=512, gt=0)
    tipo_temperature: float = Field(default=0.5, ge=0, le=2)
    tipo_top_p: float = Field(default=0.95, ge=0, le=1)
    tipo_top_k: int = Field(default=40, gt=0)

    model_config = ConfigDict(extra="ignore")


def novelai_config_defaults() -> dict[str, Any]:
    return NovelAIConfig().model_dump(mode="json")


def novelai_config_schema() -> dict[str, Any]:
    """Return a JSON Schema that only advertises TOML-representable values."""

    def remove_null_branches(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned = {key: remove_null_branches(item) for key, item in value.items()}
            for keyword in ("anyOf", "oneOf"):
                branches = cleaned.get(keyword)
                if not isinstance(branches, list):
                    continue
                non_null = [
                    branch
                    for branch in branches
                    if not (isinstance(branch, dict) and branch.get("type") == "null")
                ]
                if len(non_null) == 1:
                    cleaned.pop(keyword)
                    cleaned.update(non_null[0])
                else:
                    cleaned[keyword] = non_null
            return cleaned
        if isinstance(value, list):
            return [remove_null_branches(item) for item in value]
        return value

    schema = NovelAIConfig.model_json_schema(mode="serialization")
    cleaned = remove_null_branches(schema)
    properties = cleaned.get("properties")
    if isinstance(properties, dict):
        properties.pop("password", None)
    return cleaned


def _config_file(name: str) -> Path:
    return get_plugin_config_file(name)


def ensure_novelai_config_files() -> None:
    ensure_subplugin_config_file(
        CONFIG_FILENAME,
        novelai_config_defaults(),
        schema_basename=SCHEMA_FILENAME,
    )
    schema_path = _config_file(SCHEMA_FILENAME)
    if not schema_path.exists():
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = schema_path.with_suffix(".tmp.json")
        temp_path.write_text(
            json.dumps(
                novelai_config_schema(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp_path.replace(schema_path)


def get_novelai_config() -> NovelAIConfig:
    raw = novelai_config_defaults() | load_subplugin_config(CONFIG_FILENAME)
    raw.pop("password", None)
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
