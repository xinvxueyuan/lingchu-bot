from collections.abc import Awaitable, Callable

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot_plugin_alconna.uniseg import UniMessage

from ....utils.check import check_role_permission
from .parse_id import get_display


async def check_permission_and_send_message(
    event: GroupMessageEvent, required_roles: set[str], error_message: str
) -> bool:
    """
    通用权限检查并发送失败提示
    """
    if not await check_role_permission(event, required_roles, inherit=True):
        await UniMessage.text(error_message).send(reply_to=True)
        return False
    return True


async def check_super_and_owner(
    bot: Bot, event: GroupMessageEvent, action: str
) -> str | None:
    """
    校验超级用户权限和群主身份，返回错误信息或None
    """
    try:
        if not await check_role_permission(event, "super"):
            return f"只有超级用户才能{action}哦！"
    except ActionFailed as e:
        logger.error(f"获取机器人群身份失败: {e}")
        return "获取机器人群身份失败，请稍后再试"
    try:
        info = await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.self_id, no_cache=True
        )
    except ActionFailed as e:
        logger.error(f"获取机器人群身份失败: {e}")
        return "获取机器人群身份失败，请稍后再试"
    if info["role"] != "owner":
        return f"机器人不是群主，无法{action}！"
    return None


async def check_permissions_and_role(
    bot: Bot, event: GroupMessageEvent, action: str
) -> bool:
    """
    检查权限和机器人角色是否符合要求。
    """
    if not await check_role_permission(
        event, {"admin", "owner", "super"}, inherit=True
    ):
        await UniMessage.text(f"仅管理员、群主和超管可用: {action}").send(reply_to=True)
        return False
    if (
        await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.self_id, no_cache=True
        )
    )["role"] != "owner":
        await UniMessage.text(f"机器人不是群主，无法执行操作: {action}！").send(
            reply_to=True
        )
        return False
    return True


async def process_user_ids(
    event: GroupMessageEvent,
    user_ids: list[str],
    action: Callable[[str], Awaitable[None]],
    success_message: str,
    failure_message: str,
) -> None:
    """
    统一处理用户列表并汇总成功/失败消息
    """
    success, failed = [], []
    for uid in user_ids:
        try:
            logger.debug(
                f"{event.self_id} received command: {event.raw_message} "
                f"from user: {event.user_id} target user: {uid} "
                f"in group: {event.group_id}"
            )
            await action(uid)
            success.append(get_display(uid, event.raw_message))
        except ActionFailed as e:
            logger.error(f"Action failed for user {uid}: {e}")
            failed.append(get_display(uid, event.raw_message))
    msg = []
    if success:
        msg.append(success_message.format(users="、".join(success)))
    if failed:
        msg.append(failure_message.format(users="、".join(failed)))
    await UniMessage.text("\n".join(msg) if msg else "无用户被处理").send(reply_to=True)
