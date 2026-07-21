"""Default configuration for set_member_card handle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SetMemberCardConfig(BaseModel):
    """Configuration for set_member_card handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["SetMemberCardConfig"]
