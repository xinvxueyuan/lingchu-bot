"""Default configuration for recall_message handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecallMessageDefaults(BaseModel):
    """Defaults sub-model for recall_message handle."""

    model_config = ConfigDict(extra="ignore")

    default_count: int = 10


class RecallMessageConfig(BaseModel):
    """Configuration for recall_message handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: RecallMessageDefaults = Field(default_factory=RecallMessageDefaults)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["RecallMessageConfig"]
