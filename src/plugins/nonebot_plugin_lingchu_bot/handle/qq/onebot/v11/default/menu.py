from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

from .....menu import (
    ONEBOT_V11_ADAPTER_ID,
    menu_cmd,
    qq_menu_context,
    render_menu_for_context,
)
from ....group.common import selected_adapter_handle


@selected_adapter_handle(menu_cmd, "~onebot.v11")
async def onebot11_menu(bot: OneBot11Bot) -> Any:
    try:
        version_info = await bot.get_version_info()
    except (OneBot11ActionFailed, RuntimeError, TypeError, ValueError) as error:
        data: dict[str, Any] = {}
        logger.debug(f"Lingchu 获取 OneBot 实现信息失败: {error!r}")
    else:
        data = version_info.get("data", version_info)

    context = qq_menu_context(
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        implementation_name=_string_or_none(data.get("app_name")),
        implementation_version=_string_or_none(data.get("app_version")),
        protocol_version=_string_or_none(data.get("protocol_version")),
    )
    return await menu_cmd.finish(message=render_menu_for_context(context))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


async def import_handle() -> Any:
    return None
