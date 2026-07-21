"""Repository helpers for platform/adapter/protocol registry seeding."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..database.models import Adapter, Platform, ProtocolImplementation
from ..database.orm_crud import upsert
from ..platforms import export_registry_for_seeding

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

logger = logging.getLogger(__name__)


async def seed_registry_tables(
    session: AsyncSession | async_scoped_session,
) -> None:
    """Sync platform/adapter/protocol metadata from registry.py to database."""
    data = export_registry_for_seeding()

    for platform_data in data["platforms"]:
        try:
            await upsert(
                session,
                Platform,
                {
                    "platform_id": platform_data["platform_id"],
                    "display_name": platform_data["display_name"],
                    "capabilities": platform_data["capabilities"],
                    "implemented": platform_data["implemented"],
                },
                conflict_fields=["platform_id"],
            )
        except Exception:
            logger.exception(
                "Failed to seed platform: %s",
                platform_data.get("platform_id", "unknown"),
            )

    for adapter_data in data["adapters"]:
        try:
            await upsert(
                session,
                Adapter,
                {
                    "adapter_id": adapter_data["adapter_id"],
                    "platform_id": adapter_data["platform_id"],
                    "display_name": adapter_data["display_name"],
                    "nonebot_adapter_id": adapter_data["nonebot_adapter_id"],
                },
                conflict_fields=["adapter_id"],
            )
        except Exception:
            logger.exception(
                "Failed to seed adapter: %s",
                adapter_data.get("adapter_id", "unknown"),
            )

    for impl_data in data["protocol_implementations"]:
        try:
            await upsert(
                session,
                ProtocolImplementation,
                {
                    "protocol_id": impl_data["protocol_id"],
                    "adapter_id": impl_data["adapter_id"],
                    "display_name": impl_data["display_name"],
                    "module_path": impl_data["module_path"],
                },
                conflict_fields=["adapter_id", "protocol_id"],
            )
        except Exception:
            logger.exception(
                "Failed to seed protocol implementation: %s/%s",
                impl_data.get("adapter_id", "unknown"),
                impl_data.get("protocol_id", "unknown"),
            )

    logger.debug(
        "Registry seeding complete: %d platforms, %d adapters, %d protocols",
        len(data["platforms"]),
        len(data["adapters"]),
        len(data["protocol_implementations"]),
    )
