from importlib import import_module
from typing import Any

from nonebot import logger

from ....i18n import _async as _

__all__ = ("import_handle",)

for module_name in ("announcement", "essence", "lifecycle", "member", "profile"):
    import_module(f"{__name__}.{module_name}")


async def import_handle() -> Any:
    logger.debug(await _("导入group处理器..."))
