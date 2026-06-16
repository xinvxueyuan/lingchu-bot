from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import Event as MilkyEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from .....menu import (
    MILKY_ADAPTER_ID,
    menu_cmd,
    menu_page_cmds,
    qq_menu_context,
    render_menu_index,
    render_menu_page,
)
from ....group.common import selected_adapter_handle

milkybot_menu_pages: dict[str, Any] = {}


@selected_adapter_handle(menu_cmd, "~milky")
async def milkybot_menu(
    bot: MilkyBot,
    _event: MilkyEvent | None = None,
) -> Any:
    context = await _milky_menu_context(bot)
    return await menu_cmd.finish(message=render_menu_index(context))


def _register_milky_menu_page(page_id: str) -> None:
    command = menu_page_cmds[page_id]

    @selected_adapter_handle(command, "~milky")
    async def milkybot_menu_page(
        bot: MilkyBot,
        _event: MilkyEvent | None = None,
    ) -> Any:
        context = await _milky_menu_context(bot)
        return await command.finish(message=render_menu_page(page_id, context))

    milkybot_menu_pages[page_id] = milkybot_menu_page


for _page_id in menu_page_cmds:
    _register_milky_menu_page(_page_id)


async def _milky_menu_context(bot: MilkyBot) -> Any:
    try:
        impl_info = await bot.get_impl_info()
    except (ActionFailed, NetworkError, RuntimeError, TypeError, ValueError) as error:
        logger.debug(f"Lingchu 获取 Milky 实现信息失败: {error!r}")
        impl_name = None
        impl_version = None
    else:
        impl_name = _string_or_none(getattr(impl_info, "impl_name", None))
        impl_version = _string_or_none(getattr(impl_info, "impl_version", None))

    return qq_menu_context(
        adapter_id=MILKY_ADAPTER_ID,
        implementation_name=impl_name,
        implementation_version=impl_version,
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


async def import_handle() -> Any:
    return None
