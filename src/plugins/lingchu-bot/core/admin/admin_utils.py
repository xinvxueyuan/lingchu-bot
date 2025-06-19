"""
此模块包含用于检查目标用户权限和解析目标 QQ 号的工具函数。
"""
from typing import Optional, Tuple
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from ..lib.basic import get_bot
from ..auth.level_validator import check_qq_auth


async def check_target_permission(event: GroupMessageEvent, target_qq: int) -> bool:
    """
    检查目标用户权限，判断是否可以对目标用户进行操作。

    Args:
        event (GroupMessageEvent): 群消息事件对象。
        target_qq (int): 目标用户的 QQ 号。

    Returns:
        bool: True 表示可以操作，False 表示禁止操作。
    """
    # 若目标 QQ 号是发送者或机器人自身，则禁止操作
    if target_qq in {event.user_id, event.self_id}:
        return False
    try:
        # 获取目标用户在群里的成员信息
        member_info = await get_bot().get_group_member_info(
            group_id=event.group_id, user_id=target_qq, no_cache=True
        )
        # 若目标用户是群主或管理员，则禁止操作
        if member_info.get("role") in {"owner", "admin"}:
            return False
        # 若目标用户有特定权限，则禁止操作
        if check_qq_auth(str(target_qq)):
            return False
    except Exception:
        # 出现异常时，禁止操作
        return False
    return True


async def parse_target_qq(event: GroupMessageEvent) -> Tuple[int, Optional[Message]]:
    """
    从群消息事件中解析目标 QQ 号。

    Args:
        event (GroupMessageEvent): 群消息事件对象。

    Returns:
        Tuple[int, Optional[Message]]: 包含目标 QQ 号和错误消息的元组。
            若解析成功且可以操作，返回 (目标 QQ 号, None)；
            若解析失败或目标用户禁止操作，返回 (0, 错误消息)。
    """
    if not (
        target_qq := next(
            (
                int(seg.data["qq"])
                for seg in event.message
                if seg.type == "at" and seg.data.get("qq") != "all"
            ),
            None,
        )
    ):
        return 0, Message("请使用标准格式：操作@某人")
    return (
        (target_qq, None)
        if await check_target_permission(event, target_qq)
        else (0, Message("目标用户禁止操作"))
    )
