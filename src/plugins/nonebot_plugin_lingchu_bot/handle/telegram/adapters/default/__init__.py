"""Default Telegram handler entry point."""


async def import_handle() -> None:
    """Register Telegram handlers."""
    from . import bot_state, lifecycle, menu, moderation, mute, recall

    del bot_state, lifecycle, menu, moderation, mute, recall
