"""Default configuration for block_member handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BlockMemberDefaults(BaseModel):
    """Defaults sub-model for block_member handle."""

    model_config = ConfigDict(extra="ignore")

    block_duration: int | None = None
    default_reason: str = "违反群规"


class BlockMemberConfig(BaseModel):
    """Configuration for block_member handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: BlockMemberDefaults = Field(default_factory=BlockMemberDefaults)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["BlockMemberConfig"]
