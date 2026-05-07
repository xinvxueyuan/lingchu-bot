"""管理员管理入口。"""

from ...core.module.management.admin import (
    handle_add_admin,
    handle_remove_admin,
    remove_admin_cmd,
    add_admin_cmd,
)

__all__ = [
    "add_admin_cmd",
    "handle_add_admin",
    "handle_remove_admin",
    "remove_admin_cmd",
]
