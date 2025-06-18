from typing import Optional, Tuple
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from ..lib.basic import get_bot
from ..auth.level_validator import check_qq_auth

async def check_target_permission(event: GroupMessageEvent, target_qq: int) -> bool:
    """检查目标用户权限，返回True表示可以操作，False表示禁止操作"""
    if target_qq in {event.user_id, event.self_id}:
        return False
    try:
        member_info = await get_bot().get_group_member_info(group_id=event.group_id, user_id=target_qq, no_cache=True)
        if member_info.get("role") in {"owner", "admin"}:
            return False
        if check_qq_auth(str(target_qq)):
            return False
    except Exception:
        return False
    return True

async def parse_target_qq(event: GroupMessageEvent) -> Tuple[int, Optional[Message]]:
    """解析目标QQ号"""
    if not (target_qq := next((int(seg.data["qq"]) for seg in event.message if seg.type == "at" and seg.data.get("qq") != "all"), None)):
        return 0, Message("请使用标准格式：操作@某人")
    return (target_qq, None) if await check_target_permission(event, target_qq) else (0, Message("目标用户禁止操作"))
