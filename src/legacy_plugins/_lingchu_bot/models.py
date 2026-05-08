"""全局数据库模型入口。"""

from .core.database.model.models import (
    ChatConfig,
    ChatList,
    GlobalAdminUser,
    GlobalChatConfig,
    GlobalConfig,
    GlobalGroupConfig,
    GroupConfig,
    GroupList,
    LoginInfo,
    UiConfig,
)

__all__ = [
    "ChatConfig",
    "ChatList",
    "GlobalAdminUser",
    "GlobalChatConfig",
    "GlobalConfig",
    "GlobalGroupConfig",
    "GroupConfig",
    "GroupList",
    "LoginInfo",
    "UiConfig",
]
