from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import Event as MilkyEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from ......permissions import allowed_command_keys
from .....menu import (
    MENU_FEATURES,
    menu_cmd,
    menu_page_cmds,
    qq_menu_context,
    render_menu_index,
    render_menu_page,
)
from ....commands.common import selected_adapter_handle

MILKY_ADAPTER_ID = "~milky"
milkybot_menu_pages: dict[str, Any] = {}


@selected_adapter_handle(menu_cmd, "~milky")
async def milkybot_menu(
    bot: MilkyBot,
    _event: MilkyEvent | None = None,
) -> Any:
    context = await _milky_menu_context(bot)
    allowed = await _allowed_menu_keys(bot, _event)
    return await menu_cmd.finish(
        message=render_menu_index(context, allowed_command_keys=allowed)
    )


def _register_milky_menu_page(page_id: str) -> None:
    command = menu_page_cmds[page_id]

    @selected_adapter_handle(command, "~milky")
    async def milkybot_menu_page(
        bot: MilkyBot,
        _event: MilkyEvent | None = None,
    ) -> Any:
        context = await _milky_menu_context(bot)
        allowed = await _allowed_menu_keys(bot, _event)
        return await command.finish(
            message=render_menu_page(page_id, context, allowed_command_keys=allowed)
        )

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


async def _allowed_menu_keys(
    bot: MilkyBot,
    event: MilkyEvent | None,
) -> frozenset[str] | None:
    if event is None:
        return None
    command_keys = frozenset(feature.command_key for feature in MENU_FEATURES)
    return await allowed_command_keys(bot, event, command_keys)


async def import_handle() -> Any:
    return None
