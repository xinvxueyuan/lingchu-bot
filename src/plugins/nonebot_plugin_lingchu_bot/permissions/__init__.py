"""Public permission APIs for Lingchu Bot."""

from . import subject_policy
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
from .config import (
    PlatformPermissionMappingUpdate,
    get_platform_runtime_passthrough_config,
    update_platform_runtime_passthrough_config,
)
from .service import (
    allowed_command_keys,
    bind_platform_account,
    check_permission,
    platform_runtime_passthrough_enabled,
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
    "PlatformPermissionMappingUpdate",
    "add_identity_group_member",
    "allowed_command_keys",
    "assert_superuser",
    "bind_platform_account",
    "check_permission",
    "create_platform_identity_group",
    "delete_platform_identity_group",
    "get_platform_runtime_passthrough_config",
    "list_identity_group_members",
    "platform_runtime_passthrough_enabled",
    "remove_identity_group_member",
    "resolve_permission_context",
    "resolve_user_identity",
    "subject_policy",
    "update_platform_identity_group",
    "update_platform_runtime_passthrough_config",
    "validate_and_seed_permission_system",
]
