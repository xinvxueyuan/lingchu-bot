from typing import Any

from nonebot.adapters import Bot
from nonebot.exception import IgnoredException, MockApiException  # noqa: F401
from nonebot.message import (
    event_postprocessor,
    event_preprocessor,
    run_postprocessor,
    run_preprocessor,
)


@event_preprocessor
async def message_store_preprocessor() -> None:
    # TODO: 这里可以放一些消息预处理的代码，比如过滤掉一些不需要处理的消息等
    pass


@event_postprocessor
async def message_store_postprocessor() -> None:
    # TODO: 这里可以放一些消息后处理的代码
    pass


@run_preprocessor
async def message_store_run_preprocessor() -> None:
    # TODO: 这里可以放一些运行前处理的代码
    pass


@run_postprocessor
async def message_store_run_postprocessor() -> None:
    # TODO: 这里可以放一些运行后处理的代码
    pass


@Bot.on_calling_api
async def message_store_on_calling_api(bot: Bot, api: str, data: dict) -> None:
    # TODO: 这里可以放一些在调用API前处理的代码
    pass


@Bot.on_called_api
async def message_store_on_called_api(
    bot: Bot,
    exception: Exception | None,
    api: str,
    data: dict[str, Any],
    result: Any,
) -> None:
    # TODO: 这里可以放一些在调用API后处理的代码
    pass
