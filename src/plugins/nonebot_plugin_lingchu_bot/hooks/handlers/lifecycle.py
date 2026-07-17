"""Driver lifecycle hook handlers."""

from __future__ import annotations

import asyncio

from nonebot import get_driver, logger

from ...services.llm.mcp_lifecycle import shutdown_mcp_agent_runtime
from ...services.llm.runtime import shutdown_llm_runtime
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
    services = (
        ("scheduler", shutdown_scheduler_service),
        ("MCP Agent runtime", shutdown_mcp_agent_runtime),
        ("LLM runtime", shutdown_llm_runtime),
        ("message store", shutdown_message_store),
    )

    async def _close_services() -> asyncio.CancelledError | None:
        service_cancellation: asyncio.CancelledError | None = None
        for name, shutdown in services:
            result = (await asyncio.gather(shutdown(), return_exceptions=True))[0]
            if isinstance(result, asyncio.CancelledError):
                service_cancellation = service_cancellation or result
            elif isinstance(result, BaseException):
                logger.error("Failed to shut down {}: {}", name, type(result).__name__)
        return service_cancellation

    cleanup_task = asyncio.create_task(_close_services())
    external_cancellation: asyncio.CancelledError | None = None
    while True:
        try:
            service_cancellation = await asyncio.shield(cleanup_task)
            break
        except asyncio.CancelledError as exc:
            external_cancellation = external_cancellation or exc
            if cleanup_task.done():
                service_cancellation = cleanup_task.result()
                break

    cancellation = external_cancellation or service_cancellation
    if cancellation is not None:
        raise cancellation
