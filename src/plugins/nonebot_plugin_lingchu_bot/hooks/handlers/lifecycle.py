"""Driver lifecycle hook handlers."""

from __future__ import annotations

from nonebot import get_driver

from ...services.message_store import shutdown_message_store
from ...services.scheduler import shutdown_scheduler_service
from ...start.startup import startup

driver = get_driver()


@driver.on_startup
async def on_startup() -> None:
    """Initialize Lingchu runtime services when the NoneBot driver starts."""
    await startup()


@driver.on_shutdown
async def on_shutdown() -> None:
    """Shut down Lingchu runtime services when the NoneBot driver stops."""
    await shutdown_scheduler_service()
    await shutdown_message_store()
