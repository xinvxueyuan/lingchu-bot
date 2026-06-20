"""Repository helpers for platform/adapter/protocol registry seeding."""

from __future__ import annotations

import asyncio
import logging

from ..database.models import Adapter, Platform, ProtocolImplementation
from ..database.orm_crud import upsert
from ..platforms import export_registry_for_seeding

logger = logging.getLogger(__name__)


async def seed_registry_tables() -> None:
    """Sync platform/adapter/protocol metadata from registry.py to database."""
    data = export_registry_for_seeding()

    platform_results = await asyncio.gather(
        *(
            upsert(
                Platform,
                {
                    "platform_id": platform_data["platform_id"],
                    "display_name": platform_data["display_name"],
                    "capabilities": platform_data["capabilities"],
                    "implemented": platform_data["implemented"],
                },
                conflict_fields=["platform_id"],
            )
            for platform_data in data["platforms"]
        ),
        return_exceptions=True,
    )
    for platform_data, result in zip(data["platforms"], platform_results, strict=True):
        if isinstance(result, Exception):
            logger.error(
                "Failed to seed platform: %s",
                platform_data.get("platform_id", "unknown"),
                exc_info=result,
            )

    adapter_results = await asyncio.gather(
        *(
            upsert(
                Adapter,
                {
                    "adapter_id": adapter_data["adapter_id"],
                    "platform_id": adapter_data["platform_id"],
                    "display_name": adapter_data["display_name"],
                    "nonebot_adapter_id": adapter_data["nonebot_adapter_id"],
                },
                conflict_fields=["adapter_id"],
            )
            for adapter_data in data["adapters"]
        ),
        return_exceptions=True,
    )
    for adapter_data, result in zip(data["adapters"], adapter_results, strict=True):
        if isinstance(result, Exception):
            logger.error(
                "Failed to seed adapter: %s",
                adapter_data.get("adapter_id", "unknown"),
                exc_info=result,
            )

    protocol_results = await asyncio.gather(
        *(
            upsert(
                ProtocolImplementation,
                {
                    "protocol_id": impl_data["protocol_id"],
                    "adapter_id": impl_data["adapter_id"],
                    "display_name": impl_data["display_name"],
                    "module_path": impl_data["module_path"],
                },
                conflict_fields=["adapter_id", "protocol_id"],
            )
            for impl_data in data["protocol_implementations"]
        ),
        return_exceptions=True,
    )
    for impl_data, result in zip(
        data["protocol_implementations"], protocol_results, strict=True
    ):
        if isinstance(result, Exception):
            logger.error(
                "Failed to seed protocol implementation: %s/%s",
                impl_data.get("adapter_id", "unknown"),
                impl_data.get("protocol_id", "unknown"),
                exc_info=result,
            )

    logger.debug(
        "Registry seeding complete: %d platforms, %d adapters, %d protocols",
        len(data["platforms"]),
        len(data["adapters"]),
        len(data["protocol_implementations"]),
    )
