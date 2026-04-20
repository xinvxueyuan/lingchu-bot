"""系统模块入口。"""

from .event import handle_feat_group, handle_feat_private, handle_postprocessor
from .info import handle_framework_status, handle_system_status
from .switch import (
    feat_status_cmd,
    handle_switch,
    handle_switch_private,
    unfeat_status_cmd,
)

__all__ = [
    "feat_status_cmd",
    "handle_feat_group",
    "handle_feat_private",
    "handle_framework_status",
    "handle_postprocessor",
    "handle_switch",
    "handle_switch_private",
    "handle_system_status",
    "unfeat_status_cmd",
]
