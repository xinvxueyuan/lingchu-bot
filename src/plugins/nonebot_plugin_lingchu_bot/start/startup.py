from ..handle.command.mute import import_handle as mute_import_handle
from ..i18n import warm_translation_cache


async def startup() -> None:
    await warm_translation_cache()
    await mute_import_handle()
