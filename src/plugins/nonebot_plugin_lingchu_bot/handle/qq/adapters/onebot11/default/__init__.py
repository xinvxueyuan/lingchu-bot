from typing import Any

from . import (
    announcement as announcement,
    block as block,
    bot_state as bot_state,
    handle_defaults as handle_defaults,
    kick as kick,
    lifecycle as lifecycle,
    member as member,
    menu as menu,
    mute as mute,
    profile as profile,
    protect as protect,
    remote as remote,
)
from .menu import (
    onebot11_menu as onebot11_menu,
    onebot11_menu_pages as onebot11_menu_pages,
)


async def import_handle() -> Any:
    return None
