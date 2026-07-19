"""Default configuration for protect_member handle."""

PROTECT_MEMBER_DEFAULTS = {
    "enabled": True,
    "defaults": {"whitelist_scope": "group", "default_reason": "管理员操作"},
    "policies": {},
}
