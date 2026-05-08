"""系统开关入口。"""

from ...core.module.system.switch import (
    feat_status_cmd,
    handle_switch,
    handle_switch_private,
    unfeat_status_cmd,
)

__all__ = [
    "feat_status_cmd",
    "handle_switch",
    "handle_switch_private",
    "unfeat_status_cmd",
]
