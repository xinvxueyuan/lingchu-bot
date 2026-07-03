"""Bot connection/disconnection hook handlers."""

from __future__ import annotations

from nonebot import get_driver
from nonebot.adapters import Bot  # noqa: TC002

from ...core.async_utils import fire_and_forget
from ...services.message_store import record_bot_lifecycle
from ...services.protocol_restart_feedback import send_pending_restart_feedback

driver = get_driver()


@driver.on_bot_connect
async def on_bot_connect(bot: "Bot") -> None:
    """Record bot lifecycle and send pending restart feedback on connect."""
    fire_and_forget(
        record_bot_lifecycle(bot, "bot_connected"), name="record_bot_lifecycle"
    )
    fire_and_forget(
        send_pending_restart_feedback(bot), name="send_protocol_restart_feedback"
    )


@driver.on_bot_disconnect
async def on_bot_disconnect(bot: "Bot") -> None:
    """Record bot lifecycle on disconnect."""
    fire_and_forget(
        record_bot_lifecycle(bot, "bot_disconnected"), name="record_bot_lifecycle"
    )
