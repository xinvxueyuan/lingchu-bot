"""LLOneBot 外部 API 封装。"""

from ....core.middleware.onebot11.LLbot.api import (
    batch_kick_group_members,
    get_group_shut_list,
    send_group_notice,
)

__all__ = ["batch_kick_group_members", "get_group_shut_list", "send_group_notice"]
