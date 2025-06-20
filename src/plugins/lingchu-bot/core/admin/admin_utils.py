"""
此模块包含用于检查目标用户权限和解析目标 QQ 号的工具函数。
"""
from typing import Optional, Tuple
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from ..lib.basic import get_bot
from ..auth.level_validator import check_qq_auth


async def check_target_permission(event: GroupMessageEvent, target_qq: int) -> Tuple[bool, str]:
    """
    检查目标用户权限，返回是否允许操作及具体原因。
    """
    # 若目标 QQ 号是发送者或机器人自身，则禁止操作
    if target_qq == event.user_id:
        return False, "目标用户是操作发起者"
    if target_qq == event.self_id:
        return False, "目标用户是机器人自身"
    
    # 增加重试机制（最多重试 2 次）
    for attempt in range(2):
        try:
            # 获取目标用户在群里的成员信息（设置超时时间 5 秒）
            member_info = await get_bot().get_group_member_info(
                group_id=event.group_id, 
                user_id=target_qq, 
                no_cache=True,
                timeout=5  # 显式设置超时时间（需适配器支持）
            )
            break  # 成功获取则退出循环
        except Exception as e:
            # 仅在最后一次尝试失败时返回错误
            if attempt == 1:
                # 区分超时错误和其他错误
                if "timeout" in str(e).lower():
                    return False, "获取用户信息超时，请稍后再试"
                else:
                    return False, f"目标用户不在群内或获取信息失败: {str(e)}"
    
    # 若目标用户是群主或管理员，则禁止操作
    if member_info.get("role") in {"owner", "admin"}:
        return False, "目标用户是群主或管理员"
    
    # 若目标用户有特定权限，则禁止操作
    if check_qq_auth(str(target_qq)):
        return False, "目标用户有特殊权限"
    
    return True, "允许操作"


async def parse_target_qq(event: GroupMessageEvent) -> Tuple[int, Optional[Message]]:
    """
    从群消息事件中解析目标 QQ 号（修改后版本）。
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
    
    # 获取详细的检查结果和原因
    allow, reason = await check_target_permission(event, target_qq)
    return (
        (target_qq, None) if allow 
        else (0, Message(f"目标用户禁止操作: {reason}"))
    )
