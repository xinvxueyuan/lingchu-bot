"""头衔管理入口。"""

from ...core.module.management.special_title import (
    grant_title_cmd,
    handle_grant_title,
    handle_revoke_title,
    revoke_title_cmd,
)

__all__ = [
    "grant_title_cmd",
    "handle_grant_title",
    "handle_revoke_title",
    "revoke_title_cmd",
]
