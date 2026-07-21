"""Default configuration for restarting protocol endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RestartProtocolEndpointConfig(BaseModel):
    """Configuration for restart_protocol_endpoint handle."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    defaults: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)


__all__ = ["RestartProtocolEndpointConfig"]
