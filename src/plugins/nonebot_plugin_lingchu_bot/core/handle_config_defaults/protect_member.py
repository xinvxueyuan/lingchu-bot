"""Default configuration for protect_member handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProtectMemberDefaults(BaseModel):
    """Defaults sub-model for protect_member handle."""

    model_config = ConfigDict(extra="ignore")

    whitelist_scope: str = "group"


class ProtectMemberConfig(BaseModel):
    """Configuration for protect_member handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: ProtectMemberDefaults = Field(default_factory=ProtectMemberDefaults)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["ProtectMemberConfig"]
