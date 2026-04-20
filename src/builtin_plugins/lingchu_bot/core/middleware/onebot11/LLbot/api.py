# from http import HTTPStatus

from typing import Any

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.exception import ActionFailed, NetworkError


async def send_group_notice(
    bot: Bot, group_id: int, message: str, image: str | None = None
) -> bool:
    """
    发送群公告

    参数:
        bot: 机器人实例
        group_id: 群号
        message: 公告内容
        image: 公告图片 URL（可选）

    """
    try:
        await bot.call_api(
            api="_set_group_notice",
            group_id=group_id,
            content=message,
            image=image,
        )
    except (NetworkError, ActionFailed):
        return False
    return True


async def get_group_shut_list(bot: Bot, group_id: int) -> list[dict[str, Any]] | None:
    """
    获取被禁言群员列表

    参数:
        bot: 机器人实例
        group_id: 群号
    返回:
        成功返回被禁言成员信息列表，失败返回 None
    """
    try:
        return await bot.call_api(
            api="get_group_shut_list",
            group_id=group_id,
        )
    except (NetworkError, ActionFailed):
        return None


async def batch_kick_group_members(
    bot: Bot, group_id: int, user_ids: list[int]
) -> bool:
    """
    批量踢出群成员

    参数:
        bot: 机器人实例
        group_id: 群号
        user_ids: QQ号列表
    """
    try:
        await bot.call_api(
            api="batch_delete_group_member",
            group_id=group_id,
            user_ids=user_ids,
        )
    except (NetworkError, ActionFailed):
        return False
    return True
