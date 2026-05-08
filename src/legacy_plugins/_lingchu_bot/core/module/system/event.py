from nonebot import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
from nonebot.exception import IgnoredException
from nonebot.message import event_postprocessor, event_preprocessor

from ...middleware.onebot11.event import MessageSentEvent
from ...utils.check import check_feat_status


@event_preprocessor
async def handle_feat_group(event: GroupMessageEvent) -> None:
    if not await check_feat_status(event.self_id):
        logger.debug("框架功能开关已关闭，忽略处理")
        raise IgnoredException("框架功能开关已关闭，忽略处理")


async def handle_feat_private(event: PrivateMessageEvent) -> None:
    if not await check_feat_status(event.self_id):
        logger.debug("框架功能开关已关闭，忽略处理")
        raise IgnoredException("框架功能开关已关闭，忽略处理")


@event_postprocessor
async def handle_postprocessor(event: MessageSentEvent) -> None:
    """msg事件后处理"""
    logger.debug(f"后处理自我消息: {event.message}")
