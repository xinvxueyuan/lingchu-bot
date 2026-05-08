"""系统事件入口。"""

from ...core.module.system.event import (
    handle_feat_group,
    handle_feat_private,
    handle_postprocessor,
)

__all__ = ["handle_feat_group", "handle_feat_private", "handle_postprocessor"]
