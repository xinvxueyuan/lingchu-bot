"""Milky 默认协议实现 - 已停止维护。

此模块已从启动流程中移除，不再自动加载。
如需按需加载，请使用 tools/adapter_loader.py 工具。
"""

from typing import Any

from . import announcement as announcement
from . import block as block
from . import kick as kick
from . import lifecycle as lifecycle
from . import member as member
from . import menu as menu
from . import mute as mute
from . import profile as profile
from . import test as test
from .menu import milkybot_menu as milkybot_menu
from .menu import milkybot_menu_pages as milkybot_menu_pages


async def import_handle() -> Any:
    return None
