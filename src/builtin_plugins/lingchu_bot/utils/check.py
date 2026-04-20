"""权限检查入口。"""

from ..core.utils.check import (
    check_feat_status,
    check_role_permission,
    check_super_permission,
)

__all__ = ["check_feat_status", "check_role_permission", "check_super_permission"]
