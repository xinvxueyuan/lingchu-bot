from typing import Any

from nonebot import logger

from ....i18n import _async as _
from . import announcement, essence, lifecycle, member, profile

__all__ = ("import_handle",)

_REGISTERED_MODULES = (announcement, essence, lifecycle, member, profile)


async def import_handle() -> Any:
    logger.debug(await _("导入group处理器..."))
