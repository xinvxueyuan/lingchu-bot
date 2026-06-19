"""QQ platform identity group definitions and runtime resolution."""

from __future__ import annotations

from typing import Any

from ...permissions.types import PermissionContext, PlatformIdentityGroupSeed

QQ_PLATFORM_ID = "qq"


def get_default_identity_groups() -> tuple[PlatformIdentityGroupSeed, ...]:
    return (
        PlatformIdentityGroupSeed("qq.group", QQ_PLATFORM_ID, "QQ群聊"),
        PlatformIdentityGroupSeed(
            "qq.group.owner",
            QQ_PLATFORM_ID,
            "QQ群主",
            parent_group_id="qq.group",
        ),
        PlatformIdentityGroupSeed(
            "qq.group.admin",
            QQ_PLATFORM_ID,
            "QQ群管理员",
            parent_group_id="qq.group",
        ),
        PlatformIdentityGroupSeed(
            "qq.group.member",
            QQ_PLATFORM_ID,
            "QQ群成员",
            parent_group_id="qq.group",
        ),
        PlatformIdentityGroupSeed("qq.friend", QQ_PLATFORM_ID, "QQ好友"),
        PlatformIdentityGroupSeed("qq.channel", QQ_PLATFORM_ID, "QQ频道"),
        PlatformIdentityGroupSeed("qq.bot", QQ_PLATFORM_ID, "QQ机器人"),
        PlatformIdentityGroupSeed("qq.device", QQ_PLATFORM_ID, "QQ设备"),
    )


async def resolve_runtime_identity_groups(
    bot: Any,
    event: Any,
    context: PermissionContext,
) -> frozenset[str]:
    _ = bot
    if context.scope_type != "group":
        return frozenset()

    role = _event_role(event)
    if role == "owner":
        return frozenset({"qq.group", "qq.group.owner"})
    if role == "admin":
        return frozenset({"qq.group", "qq.group.admin"})
    return frozenset({"qq.group", "qq.group.member"})


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
