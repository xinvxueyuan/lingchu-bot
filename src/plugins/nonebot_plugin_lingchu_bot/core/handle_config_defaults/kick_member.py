"""Default configuration for kick_member handle."""

KICK_MEMBER_DEFAULTS = {
    "enabled": True,
    "defaults": {"require_reason": False, "audit_level": "low"},
    "policies": {},
}
