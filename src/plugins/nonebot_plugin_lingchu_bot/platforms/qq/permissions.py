"""QQ platform identity group definitions and runtime resolution."""

from __future__ import annotations

import logging
from typing import Any

from ...permissions.types import PermissionContext, PlatformIdentityGroupSeed

logger = logging.getLogger(__name__)

PLATFORM_ID = "qq"


def get_default_identity_groups() -> tuple[PlatformIdentityGroupSeed, ...]:
    return (
        PlatformIdentityGroupSeed("qq.group", PLATFORM_ID, "QQ群聊"),
        PlatformIdentityGroupSeed(
            "qq.group.owner",
            PLATFORM_ID,
            "QQ群主",
            parent_group_id="qq.group",
        ),
        PlatformIdentityGroupSeed(
            "qq.group.admin",
            PLATFORM_ID,
            "QQ群管理员",
            parent_group_id="qq.group",
        ),
        PlatformIdentityGroupSeed(
            "qq.group.member",
            PLATFORM_ID,
            "QQ群成员",
            parent_group_id="qq.group",
        ),
        PlatformIdentityGroupSeed("qq.friend", PLATFORM_ID, "QQ好友"),
        PlatformIdentityGroupSeed("qq.channel", PLATFORM_ID, "QQ频道"),
        PlatformIdentityGroupSeed("qq.bot", PLATFORM_ID, "QQ机器人"),
        PlatformIdentityGroupSeed("qq.device", PLATFORM_ID, "QQ设备"),
    )


async def resolve_runtime_identity_groups(
    bot: Any,
    event: Any,
    context: PermissionContext,
) -> frozenset[str]:
    if context.scope_type != "group":
        return frozenset()

    role = _event_role(event)
    if role is None:
        role = await _fetch_role_from_api(bot, context)
    if role == "owner":
        return frozenset({"qq.group", "qq.group.owner"})
    if role == "admin":
        return frozenset({"qq.group", "qq.group.admin"})
    return frozenset({"qq.group", "qq.group.member"})


async def _fetch_role_from_api(
    bot: Any,
    context: PermissionContext,
) -> str | None:
    """Fetch user role via OneBot V11 get_group_member_info API."""
    if context.scope_id is None or context.account_id is None:
        return None
    try:
        info = await bot.call_api(
            "get_group_member_info",
            group_id=int(context.scope_id),
            user_id=int(context.account_id),
        )
    except Exception:
        logger.warning(
            "get_group_member_info failed for group=%s user=%s, "
            "falling back to member role",
            context.scope_id,
            context.account_id,
        )
        return "member"
    role = info.get("role") if isinstance(info, dict) else getattr(info, "role", None)
    if role in {"owner", "admin", "member"}:
        return str(role)
    return None


def _event_role(event: Any) -> str | None:
    sender = getattr(event, "sender", None)
    role = getattr(sender, "role", None)
    if role in {"owner", "admin", "member"}:
        return str(role)

    data = getattr(event, "data", None)
    data_sender = getattr(data, "sender", None)
    data_role = getattr(data_sender, "role", None)
    if data_role in {"owner", "admin", "member"}:
        return str(data_role)
    return None
