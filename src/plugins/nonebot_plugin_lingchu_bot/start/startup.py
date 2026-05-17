from ..handle.command.mute import import_handle as mute_import_handle


async def startup() -> None:
    await mute_import_handle()
