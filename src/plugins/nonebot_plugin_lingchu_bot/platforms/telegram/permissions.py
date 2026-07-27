"""Telegram platform identity groups and runtime resolution."""

from __future__ import annotations

import logging
from typing import Any

from nonebot.adapters.telegram.exception import ActionFailed, NetworkError

from ...permissions.types import PermissionContext, PlatformIdentityGroupSeed

PLATFORM_ID = "telegram"
logger = logging.getLogger(__name__)


def get_default_identity_groups() -> tuple[PlatformIdentityGroupSeed, ...]:
    return (
        PlatformIdentityGroupSeed("telegram.group", PLATFORM_ID, "Telegram Group"),
        PlatformIdentityGroupSeed(
            "telegram.group.owner",
            PLATFORM_ID,
            "Telegram Group Owner",
            parent_group_id="telegram.group",
        ),
        PlatformIdentityGroupSeed(
            "telegram.group.admin",
            PLATFORM_ID,
            "Telegram Group Administrator",
            parent_group_id="telegram.group",
        ),
        PlatformIdentityGroupSeed(
            "telegram.group.member",
            PLATFORM_ID,
            "Telegram Group Member",
            parent_group_id="telegram.group",
        ),
        PlatformIdentityGroupSeed("telegram.private", PLATFORM_ID, "Telegram Private"),
        PlatformIdentityGroupSeed("telegram.channel", PLATFORM_ID, "Telegram Channel"),
        PlatformIdentityGroupSeed("telegram.bot", PLATFORM_ID, "Telegram Bot"),
    )


async def resolve_runtime_identity_groups(
    bot: Any,
    event: Any,
    context: PermissionContext,
) -> frozenset[str]:
    if context.scope_type != "group":
        return frozenset()
    status = getattr(getattr(event, "sender", None), "status", None)
    if status is None:
        chat_id = getattr(getattr(event, "chat", None), "id", None)
        user_id = getattr(getattr(event, "from_", None), "id", None)
        if chat_id is None or user_id is None:
            return frozenset()
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        except (ActionFailed, NetworkError):
            logger.warning(
                "Telegram get_chat_member failed for chat=%s user=%s",
                chat_id,
                user_id,
            )
            return frozenset()
        status = getattr(member, "status", None)
    role_group = {
        "creator": "telegram.group.owner",
        "administrator": "telegram.group.admin",
        "member": "telegram.group.member",
        "restricted": "telegram.group.member",
    }.get(status if isinstance(status, str) else "")
    return (
        frozenset({"telegram.group", role_group})
        if role_group is not None
        else frozenset()
    )
