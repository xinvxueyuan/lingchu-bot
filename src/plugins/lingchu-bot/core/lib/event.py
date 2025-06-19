"""
此模块定义了用于检查群聊管理权限的辅助函数和规则。
"""
from ..auth.level_validator import check_qq_auth
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent, NoticeEvent, GroupBanNoticeEvent

def is_group_admin(event: MessageEvent) -> bool:
    """
    检查事件是否为群聊管理事件。

    该函数会依次检查事件是否为群消息、用户是否有特殊权限，
    最后检查用户是否为群主或管理员。

    Args:
        event (MessageEvent): 消息事件对象。

    Returns:
        bool: 如果用户具有群管理权限则返回 True，否则返回 False。
    """
    # 步骤 1: 检查是否为群消息
    if not isinstance(event, GroupMessageEvent):
        return False

    # 步骤 2: 检查用户权限等级
    qq = str(event.user_id)
    auth_level = check_qq_auth(qq)
    if auth_level:
        # 若用户满足特殊权限，直接判定为具有群管理权限
        return True

    # 步骤 3: 检查用户是否为群主或管理员
    return getattr(event.sender, "role", None) in ["owner", "admin"]

# 定义一个 NoneBot 规则，使用 is_group_admin 函数进行权限检查
admin_rule = Rule(is_group_admin)
