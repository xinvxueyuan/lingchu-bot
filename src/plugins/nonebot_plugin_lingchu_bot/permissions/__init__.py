"""Public permission APIs for Lingchu Bot."""

from .admin import (
    PermissionDeniedError,
    add_identity_group_member,
    assert_superuser,
    create_platform_identity_group,
    delete_platform_identity_group,
    list_identity_group_members,
    remove_identity_group_member,
    update_platform_identity_group,
)
from .bootstrap import PermissionConfigError, validate_and_seed_permission_system
from .service import (
    allowed_command_keys,
    bind_platform_account,
    check_permission,
    resolve_permission_context,
    resolve_user_identity,
)
from .types import (
    PermissionContext,
    PermissionDecision,
    PlatformIdentityGroupSeed,
)

__all__ = [
    "PermissionConfigError",
    "PermissionContext",
    "PermissionDecision",
    "PermissionDeniedError",
    "PlatformIdentityGroupSeed",
    "add_identity_group_member",
    "allowed_command_keys",
    "assert_superuser",
    "bind_platform_account",
    "check_permission",
    "create_platform_identity_group",
    "delete_platform_identity_group",
    "list_identity_group_members",
    "remove_identity_group_member",
    "resolve_permission_context",
    "resolve_user_identity",
    "update_platform_identity_group",
    "validate_and_seed_permission_system",
]
