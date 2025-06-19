from .basic import *

async def manage_user_mute(group_id: int, user_id: int, duration: int):
    """
    管理用户禁言状态
    
    Args:
        group_id: 群号
        user_id: 用户QQ号
        duration: 禁言时长(秒)，0表示解禁
    """
    try:
        await get_bot().set_group_ban(
            group_id=group_id,
            user_id=user_id,
            duration=duration
        )
        return True
    except Exception:
        return False


async def manage_group_mute_all(group_id: int, enable: bool):
    """
    管理全员禁言状态
    
    Args:
        group_id: 群号
        enable: True开启全员禁言，False关闭全员禁言
    """
    try:
        await get_bot().set_group_whole_ban(
            group_id=group_id,
            enable=enable
        )
        return True
    except Exception:
        return False


async def manage_group_kick(group_id: int, user_id: int, reject_add_request: bool = False):
    """
    管理群成员踢出
    
    Args:
        group_id: 群号
        user_id: 用户QQ号
        reject_add_request: 是否拒绝再次加群申请，默认为False
    """
    try:
        await get_bot().set_group_kick(
            group_id=group_id,
            user_id=user_id,
            reject_add_request=reject_add_request
        )
        return True
    except Exception:
        return False
    
async def manage_group_leave(group_id: int, is_dismiss: bool = False):
    """
    管理群成员退群或解散群
    
    Args:
        group_id: 群号
        is_dismiss: 是否解散群，默认为False表示仅退群
    """
    try:
        if is_dismiss:
            await get_bot().set_group_dismiss(group_id=group_id)
        else:
            await get_bot().set_group_leave(group_id=group_id)
        return True
    except Exception:
        return False


async def check_bot_admin_status(group_id: int) -> bool:
    """
    检查机器人是否有群管理员或群主权限
    
    Args:
        group_id: 群号
        
    Returns:
        bool: True表示有权限，False表示无权限
    """
    try:
        bot_info = await get_bot().get_group_member_info(
            group_id=group_id,
            user_id=get_bot().self_id
        )
        role = bot_info.get("role")
        return role in ["owner", "admin"]
    except Exception:
        return False


async def manage_group_notice(group_id: int, content: str, image: str | None = None):
    """
    发送群公告
    
    Args:
        group_id: 群号
        content: 公告内容
        image: 公告图片URL(可选)，默认为None
        
    Returns:
        bool: True表示发送成功，False表示发送失败
    """
    try:
        await get_bot()._send_group_notice(
            group_id=group_id,
            content=content,
            image=image
        )
        return True
    except Exception:
        return False


async def get_group_muted_list(group_id: int) -> list:
    """
    获取群禁言成员列表
    
    Args:
        group_id: 群号
        
    Returns:
        list: 被禁言成员信息列表，格式为[{"user_id": int, "nickname": str, "time_left": int}]
              如果获取失败返回空列表
    """
    try:
        member_list = await get_bot().get_group_member_list(group_id=group_id)
        muted_members = [
            {
                "user_id": member["user_id"],
                "nickname": member["nickname"],
                "time_left": member["shut_up_timestamp"] - int(time.time())
            }
            for member in member_list 
            if member.get("shut_up_timestamp", 0) > time.time()
        ]
        return muted_members
    except Exception:
        return []
