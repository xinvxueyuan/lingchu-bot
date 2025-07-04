"""
管理员工具模块

此模块提供用于检查目标用户权限和解析目标QQ号的实用函数，
主要用于处理群聊中的管理员操作验证。
"""

from typing import Optional, Tuple
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from ..lib.basic import get_bot
from ..auth.level_validator import check_qq_auth


async def check_target_permission(event: GroupMessageEvent, target_qq: int) -> Tuple[bool, str]:
    """检查对目标用户的操作权限
    
    Args:
        event: 群消息事件对象
        target_qq: 目标用户的QQ号
        
    Returns:
        Tuple[bool, str]: (是否允许操作, 原因说明)
    """
    # 基础权限检查
    if target_qq == event.user_id:
        return False, "目标用户是操作发起者"
    if target_qq == event.self_id:
        return False, "目标用户是机器人自身"
    
    # 带重试机制的成员信息获取
    for attempt in range(2):
        try:
            member_info = await get_bot().get_group_member_info(
                group_id=event.group_id, 
                user_id=target_qq, 
                no_cache=True,
                timeout=5
            )
            break
        except Exception as e:
            if attempt == 1:
                error_msg = "获取用户信息超时，请稍后再试" if "timeout" in str(e).lower() \
                    else f"目标用户不在群内或获取信息失败: {str(e)}"
                return False, error_msg
    
    # 角色权限检查
    if member_info.get("role") in {"owner", "admin"}:
        return False, "目标用户是群主或管理员"
    
    # 特殊权限检查
    if check_qq_auth(str(target_qq)):
        return False, "目标用户有特殊权限"
    
    return True, "允许操作"


async def parse_target_qq(event: GroupMessageEvent) -> Tuple[int, Optional[Message]]:
    """从群消息中解析目标QQ号
    
    解析消息中的@提及，并验证目标用户的操作权限
    
    Args:
        event: 群消息事件对象
        
    Returns:
        Tuple[int, Optional[Message]]: 
            - 成功时返回(目标QQ号, None)
            - 失败时返回(0, 错误消息)
    """
    # 提取消息中的@提及
    target_qq = next(
        (int(seg.data["qq"]) for seg in event.message 
         if seg.type == "at" and seg.data.get("qq") != "all"),
        None
    )
    
    if not target_qq:
        return 0, Message("请使用标准格式：操作@某人")
    
    # 验证目标用户权限
    allow, reason = await check_target_permission(event, target_qq)
    return (target_qq, None) if allow else (0, Message(f"目标用户禁止操作: {reason}"))