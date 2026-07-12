from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any, Final

from nonebot import logger

from ..i18n import _async as _

_RESTART_FEEDBACK_TTL_SECONDS: Final[float] = 300.0
_ONEBOT11_ADAPTER_NAME: Final[str] = "OneBot V11"
_QQ_PLATFORM_ID: Final[str] = "qq"
_ONEBOT11_ADAPTER_ID: Final[str] = "~onebot.v11"


@dataclass(frozen=True, slots=True)
class PendingRestartFeedback:
    platform_id: str
    adapter_id: str
    bot_id: str
    conversation_type: str
    conversation_id: str
    created_at: float


_pending_feedback: dict[tuple[str, str, str], PendingRestartFeedback] = {}


def clear_pending_restart_feedback() -> None:
    _pending_feedback.clear()


def clear_pending_restart_feedback_for(
    *, platform_id: str, adapter_id: str, bot_id: str
) -> bool:
    key = (platform_id, adapter_id, bot_id)
    return _pending_feedback.pop(key, None) is not None


def list_pending_restart_feedback() -> tuple[PendingRestartFeedback, ...]:
    _drop_expired_pending_feedback()
    return tuple(_pending_feedback.values())


def register_pending_restart_feedback(
    *,
    platform_id: str,
    adapter_id: str,
    bot_id: str,
    conversation_type: str,
    conversation_id: str,
) -> None:
    _drop_expired_pending_feedback()
    key = (platform_id, adapter_id, bot_id)
    _pending_feedback[key] = PendingRestartFeedback(
        platform_id=platform_id,
        adapter_id=adapter_id,
        bot_id=bot_id,
        conversation_type=conversation_type,
        conversation_id=conversation_id,
        created_at=monotonic(),
    )


async def send_pending_restart_feedback(bot: Any) -> bool:
    _drop_expired_pending_feedback()
    if _adapter_name(bot) != _ONEBOT11_ADAPTER_NAME:
        return False

    bot_id = str(getattr(bot, "self_id", ""))
    key = (_QQ_PLATFORM_ID, _ONEBOT11_ADAPTER_ID, bot_id)
    pending = _pending_feedback.get(key)
    if pending is None:
        return False

    if pending.conversation_type != "group":
        return False
    if not await _is_reconnected_onebot11_ready(bot, expected_bot_id=pending.bot_id):
        return False

    try:
        await bot.send_group_msg(
            group_id=int(pending.conversation_id),
            message=await _("协议端已重启并重新连接"),
        )
    except Exception:
        logger.exception("Failed to send protocol restart feedback")
        return False
    else:
        _pending_feedback.pop(key, None)
        return True


async def _is_reconnected_onebot11_ready(bot: Any, *, expected_bot_id: str) -> bool:
    try:
        login_info = await bot.get_login_info()
    except Exception:
        logger.exception("Failed to verify protocol restart login account")
        return False

    if not isinstance(login_info, dict):
        return False
    if str(login_info.get("user_id", "")) != expected_bot_id:
        return False

    try:
        status = await bot.get_status()
    except Exception:
        logger.exception("Failed to verify protocol restart status")
        return False

    if not isinstance(status, dict):
        return False
    return status.get("good") is True and status.get("online") is not False


def _adapter_name(bot: Any) -> str | None:
    adapter = getattr(bot, "adapter", None)
    get_name = getattr(adapter, "get_name", None)
    if get_name is None:
        return None
    return str(get_name())


def _drop_expired_pending_feedback() -> None:
    now = monotonic()
    expired = [
        key
        for key, pending in _pending_feedback.items()
        if now - pending.created_at > _RESTART_FEEDBACK_TTL_SECONDS
    ]
    for key in expired:
        _pending_feedback.pop(key, None)
