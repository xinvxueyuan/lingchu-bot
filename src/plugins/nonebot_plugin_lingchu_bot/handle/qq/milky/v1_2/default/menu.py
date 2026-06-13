from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from .....menu import (
    MILKY_ADAPTER_ID,
    menu_cmd,
    qq_menu_context,
    render_menu_for_context,
)
from ....group.common import selected_adapter_handle


@selected_adapter_handle(menu_cmd, "~milky")
async def milkybot_menu(bot: MilkyBot) -> Any:
    try:
        impl_info = await bot.get_impl_info()
    except (ActionFailed, NetworkError, RuntimeError, TypeError, ValueError) as error:
        logger.debug(f"Lingchu 获取 Milky 实现信息失败: {error!r}")
        impl_name = None
        impl_version = None
    else:
        impl_name = _string_or_none(getattr(impl_info, "impl_name", None))
        impl_version = _string_or_none(getattr(impl_info, "impl_version", None))

    context = qq_menu_context(
        adapter_id=MILKY_ADAPTER_ID,
        implementation_name=impl_name,
        implementation_version=impl_version,
    )
    return await menu_cmd.finish(message=render_menu_for_context(context))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


async def import_handle() -> Any:
    return None
