"""LLOneBot 适配器扩展入口。"""

from .api import batch_kick_group_members, get_group_shut_list, send_group_notice

__all__ = ["batch_kick_group_members", "get_group_shut_list", "send_group_notice"]
