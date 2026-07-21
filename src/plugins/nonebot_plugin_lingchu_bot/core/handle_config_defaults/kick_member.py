"""Default configuration for kick_member handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KickMemberDefaults(BaseModel):
    """Defaults sub-model for kick_member handle."""

    model_config = ConfigDict(extra="ignore")

    require_reason: bool = False
    audit_level: str = "low"


class KickMemberConfig(BaseModel):
    """Configuration for kick_member handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: KickMemberDefaults = Field(default_factory=KickMemberDefaults)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["KickMemberConfig"]
