"""Default configuration for remote_mute handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RemoteMuteDefaults(BaseModel):
    """Defaults sub-model for remote_mute handle."""

    model_config = ConfigDict(extra="ignore")

    mute_duration: int = 60
    default_reason: str = "管理员操作"


class RemoteMuteConfig(BaseModel):
    """Configuration for remote_mute handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: RemoteMuteDefaults = Field(default_factory=RemoteMuteDefaults)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["RemoteMuteConfig"]
