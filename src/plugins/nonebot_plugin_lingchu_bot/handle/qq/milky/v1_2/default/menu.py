from typing import Any

from .....menu import menu_cmd, render_menu
from ....group.common import selected_adapter_handle


@selected_adapter_handle(menu_cmd, "~milky")
async def milkybot_menu() -> Any:
    return await menu_cmd.finish(message=render_menu())


async def import_handle() -> Any:
    return None
