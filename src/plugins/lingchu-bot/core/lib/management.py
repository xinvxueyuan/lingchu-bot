from .basic import *

async def manage_user_mute(group_id: int, user_id: int, duration: int) -> bool:
    """
    管理用户禁言状态
    
    Args:
        group_id: 群号
        user_id: 要禁言的用户QQ号
        duration: 禁言时长(秒)，0表示解禁
    
    Returns:
        bool: 操作是否成功
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


async def manage_group_mute_all(group_id: int, enable: bool) -> bool:
    """
    管理全员禁言状态
    
    Args:
        group_id: 群号
        enable: 是否开启全员禁言
    
    Returns:
        bool: 操作是否成功
    """
    try:
        await get_bot().set_group_whole_ban(
            group_id=group_id,
            enable=enable
        )
        return True
    except Exception:
        return False


async def manage_group_kick(
    group_id: int, 
    user_id: int, 
    reject_add_request: bool = False
) -> bool:
    """
    踢出群成员
    
    Args:
        group_id: 群号
        user_id: 要踢出的用户QQ号
        reject_add_request: 是否拒绝该用户再次加群
    
    Returns:
        bool: 操作是否成功
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


async def manage_group_leave(group_id: int, is_dismiss: bool = False) -> bool:
    """
    退出群聊或解散群
    
    Args:
        group_id: 群号
        is_dismiss: 是否解散群(仅群主可用)
    
    Returns:
        bool: 操作是否成功
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
    检查机器人在群内的管理权限
    
    Args:
        group_id: 群号
    
    Returns:
        bool: 是否有管理员或群主权限
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


async def manage_group_notice(
    group_id: int, 
    content: str, 
    image: str | None = None
) -> bool:
    """
    发送群公告
    
    Args:
        group_id: 群号
        content: 公告文本内容
        image: 公告图片URL(可选)
    
    Returns:
        bool: 发送是否成功
    """
    try:
        if image:
            await get_bot()._send_group_notice(
                group_id=group_id,
                content=content,
                image=image,
                is_confirmed=False
            )
        else:
            await get_bot()._send_group_notice(
                group_id=group_id,
                content=content,
                is_confirmed=False
            )
        return True
    except Exception as e:
        logger.error(f"发送群公告失败: {e}")
        return False


async def get_group_muted_list(group_id: int) -> list[dict]:
    """
    获取当前被禁言的成员列表
    
    Args:
        group_id: 群号
    
    Returns:
        list: 包含被禁言成员信息的列表，每个成员信息为:
              {
                  "user_id": 用户QQ号,
                  "nickname": 昵称,
                  "time_left": 剩余禁言时间(秒)
              }
              获取失败时返回空列表
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
