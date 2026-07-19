"""Default configuration for restarting protocol endpoints."""

from typing import Any

RESTART_PROTOCOL_ENDPOINT_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "defaults": {"default_platform": "当前平台"},
    "policies": {},
}
