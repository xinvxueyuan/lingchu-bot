"""Default configuration for member_mute handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemberMuteDefaults(BaseModel):
    """Defaults sub-model for member_mute handle."""

    model_config = ConfigDict(extra="ignore")

    mute_duration: int = 300
    default_reason: str = "管理员操作"


class MemberMuteConfig(BaseModel):
    """Configuration for member_mute handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: MemberMuteDefaults = Field(default_factory=MemberMuteDefaults)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["MemberMuteConfig"]
