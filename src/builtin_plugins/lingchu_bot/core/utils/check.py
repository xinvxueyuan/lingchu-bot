"""检查辅助函数"""


async def check_feat_status(login_id: int) -> bool:
    """检查功能开关状态，返回True表示开启，False表示关闭"""

    from ..database import client
    from ..database.model import models

    obj, status = await client.get_one(
        model=models.LoginInfo, filters={"login_id": login_id}
    )
    return status and obj is not None and getattr(obj, "feat_status", False)


# =============================================================================
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent


def _is_super_user(user_id: str, super_users: set[str]) -> bool:
    return str(user_id) in {str(uid) for uid in super_users}


def _get_event_role(event: GroupMessageEvent) -> str:
    return getattr(event.sender, "role", "member")


def _get_role_level(role: str) -> int:
    role_level = {"member": 0, "admin": 1, "owner": 2, "super": 3}
    return role_level.get(role, 0)


def _normalize_roles(role: str | set[str]) -> set[str]:
    return {role} if isinstance(role, str) else set(role)


async def check_role_permission(
    event: GroupMessageEvent, role: str | set[str], *, inherit: bool = False
) -> bool:
    """
    检查群消息事件角色权限
    event: 群消息事件
    role: 目标角色(str)或角色组(set[str])，可为 'super', 'owner', 'admin', 'member'
    inherit: 是否允许权限继承（更高权限可通过，组匹配时无继承）
    """
    import nonebot

    target_roles = {str(r) for r in _normalize_roles(role)}
    if not target_roles:
        return False
    is_super = _is_super_user(
        str(event.user_id), nonebot.get_driver().config.superusers
    )
    event_role = str(_get_event_role(event))

    result = False
    if "super" in target_roles:
        if len(target_roles) > 1:
            result = is_super or event_role in target_roles
        else:
            result = is_super
    elif len(target_roles) > 1:
        result = event_role in target_roles
    else:
        target = next(iter(target_roles))
        if target == "super":
            result = is_super
        elif target in {"member", "admin", "owner"}:
            if inherit:
                result = is_super or _get_role_level(event_role) >= _get_role_level(
                    target
                )
            else:
                result = event_role == target
        else:
            result = False
    return result


# =============================================================================
async def check_super_permission(event: PrivateMessageEvent) -> bool:
    """
    检查是否为超级用户，仅适用于无角色区分的事件（如私聊事件）。
    """
    import nonebot

    return _is_super_user(str(event.user_id), nonebot.get_driver().config.superusers)
