"""Default configuration for remote_block handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RemoteBlockDefaults(BaseModel):
    """Defaults sub-model for remote_block handle."""

    model_config = ConfigDict(extra="ignore")

    block_duration: int | None = None
    default_reason: str = "违反群规"


class RemoteBlockConfig(BaseModel):
    """Configuration for remote_block handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: RemoteBlockDefaults = Field(default_factory=RemoteBlockDefaults)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["RemoteBlockConfig"]
