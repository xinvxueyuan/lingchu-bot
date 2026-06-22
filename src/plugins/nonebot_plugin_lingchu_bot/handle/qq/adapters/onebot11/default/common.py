from collections.abc import Awaitable, Callable
from typing import Any, Final

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as Onebot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as Onebot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import (
    ActionFailed as Onebot11ActionFailed,
)
from nonebot_plugin_alconna.uniseg import At

from ......i18n import _async as _
from ......repositories.blocklist import (
    BlockScope,
    expires_at_from_duration,
    upsert_block,
)
from ....commands.common import GroupCommand

QQ_PLATFORM_ID: Final[str] = "qq"
ONEBOT_V11_ADAPTER_ID: Final[str] = "~onebot.v11"
MUTE_DURATION_MIN: Final[int] = 1
MUTE_DURATION_MAX: Final[int] = 30 * 24 * 60 * 60  # 30 天

type GroupAction = Callable[[], Awaitable[Any]]


async def target_user_onebot11(
    user: At, bot: Onebot11Bot, event: Onebot11GroupMessageEvent
) -> tuple[int, str]:
    try:
        target_user_id: int = int(user.target)
    except (TypeError, ValueError) as error:
        msg = f"无效的用户 ID: {user.target!r}"
        raise ValueError(msg) from error

    if user.display:
        return target_user_id, user.display

    try:
        member_info = await bot.get_group_member_info(
            group_id=event.group_id, user_id=target_user_id
        )
        name = member_info.get("card") or member_info.get("nickname") or ""
        if name:
            return target_user_id, str(name)
    except Onebot11ActionFailed:
        logger.debug(
            f"获取群成员信息失败: group_id={event.group_id}, user_id={target_user_id}"
        )

    return target_user_id, ""


async def resolve_user_onebot11(
    user: At | int, bot: Onebot11Bot, event: Onebot11GroupMessageEvent
) -> tuple[int, str]:
    """解析用户目标，支持 At 对象或直接的 user_id。

    由于 QQ 平台限制，@ 功能无法定位到目标用户，因此支持直接传入 user_id。

    Args:
        user: At 对象或 user_id (int)
        bot: OneBot V11 Bot 实例
        event: 群消息事件

    Returns:
        tuple[int, str]: (user_id, display_name)
    """
    if isinstance(user, int):
        # 直接传入 user_id，尝试获取昵称
        try:
            member_info = await bot.get_group_member_info(
                group_id=event.group_id, user_id=user
            )
            name = member_info.get("card") or member_info.get("nickname") or ""
            return user, str(name)
        except Onebot11ActionFailed:
            logger.debug(
                f"获取群成员信息失败: group_id={event.group_id}, user_id={user}"
            )
        return user, ""

    return await target_user_onebot11(user, bot, event)


async def finish_action_error_onebot11(
    command: GroupCommand,
    operation: str,
    error: Onebot11ActionFailed,
) -> Any:
    logger.error(f"{operation}失败，操作被拒绝: {error!r}")
    return await command.finish(
        message=(await _("{operation}失败，操作被拒绝: {error!r}")).format(
            operation=operation, error=error
        )
    )


async def run_group_action_onebot11(
    command: GroupCommand,
    operation: str,
    action: GroupAction,
    success_message: str,
) -> Any:
    try:
        await action()
    except Onebot11ActionFailed as error:
        return await finish_action_error_onebot11(command, operation, error)

    logger.info(success_message)
    return await command.finish(message=success_message)


def bot_self_id_safe(bot: Onebot11Bot) -> int | None:
    """安全获取机器人 self_id，无法转换时返回 None"""
    try:
        return int(bot.self_id)
    except (ValueError, TypeError):
        return None


def bot_id(bot: Onebot11Bot) -> str:
    return str(getattr(bot, "self_id", ""))


async def default_block_reason(reason: str | None) -> str:
    """获取默认拉黑原因"""
    return await _("违反群规「默认」") if reason is None else reason


async def default_admin_reason(reason: str | None) -> str:
    """获取默认管理操作原因"""
    return await _("管理员操作「默认」") if reason is None else reason


async def check_self_target(
    target_user_id: int,
    bot: Onebot11Bot,
    event: Onebot11GroupMessageEvent,
    cmd_matcher: Any,
    action_name: str,
) -> bool:
    """检查是否尝试操作自己或机器人。返回 True 表示通过检查。"""
    if target_user_id == event.user_id:
        msg = await _("不能{action}自己")
        await cmd_matcher.finish(msg.format(action=action_name))
        return False

    bot_self = bot_self_id_safe(bot)
    if bot_self is not None and target_user_id == bot_self:
        msg = await _("不能{action}机器人")
        await cmd_matcher.finish(msg.format(action=action_name))
        return False

    return True


async def store_block_record(  # noqa: PLR0913
    *,
    scope: BlockScope,
    group_id: int,
    user_id: int,
    operator_id: int,
    duration: int | None,
    reason: str | None,
    bot: Onebot11Bot,
) -> None:
    """存储黑名单记录（本地和远程统一入口）"""
    await upsert_block(
        platform_id=QQ_PLATFORM_ID,
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        bot_id=bot_id(bot),
        scope=scope,
        group_id=group_id,
        user_id=user_id,
        operator_id=operator_id,
        reason=reason,
        expires_at=expires_at_from_duration(duration),
    )


async def check_target_privilege(
    bot: Onebot11Bot,
    event: Onebot11GroupMessageEvent,
    target_user_id: int,
    cmd_matcher: Any,
) -> bool:
    """检查目标用户权限是否过高。返回 True 表示通过检查。

    如果目标用户是管理员或群主，且操作者不是群主或超级用户，则拒绝操作。
    """
    # 获取目标用户角色
    try:
        member_info = await bot.get_group_member_info(
            group_id=event.group_id, user_id=target_user_id, no_cache=True
        )
    except Onebot11ActionFailed:
        # 无法获取目标用户信息，允许操作（让 API 层处理）
        return True

    target_role = member_info.get("role", "member")
    if target_role not in ("admin", "owner"):
        return True

    # 目标是管理员或群主，检查操作者权限
    try:
        operator_info = await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.user_id, no_cache=True
        )
    except Onebot11ActionFailed:
        await cmd_matcher.finish(await _("无法验证操作权限"))
        return False

    operator_role = operator_info.get("role", "member")
    if operator_role == "owner":
        return True  # 群主可以操作任何人

    # 检查是否为超级用户
    from nonebot import get_driver

    superusers = get_driver().config.superusers
    if str(event.user_id) in superusers:
        return True

    await cmd_matcher.finish(await _("目标用户权限过高，无法执行"))
    return False


async def check_bot_privilege(
    bot: Onebot11Bot,
    group_id: int,
    cmd_matcher: Any,
) -> bool:
    """检查机器人是否在目标群中具有管理员/群主权限。返回 True 表示通过检查。"""
    try:
        bot_info = await bot.get_group_member_info(
            group_id=group_id, user_id=int(bot.self_id), no_cache=True
        )
    except (Onebot11ActionFailed, ValueError, TypeError):
        await cmd_matcher.finish(await _("机器人缺少管理员权限"))
        return False

    role = bot_info.get("role", "member")
    if role not in ("admin", "owner"):
        await cmd_matcher.finish(await _("机器人缺少管理员权限"))
        return False
    return True


async def record_command_audit(  # noqa: PLR0913
    bot: Onebot11Bot,
    event: Onebot11GroupMessageEvent,
    *,
    action: str,
    target_user_id: int | None = None,
    reason: str | None = None,
    duration: int | None = None,
    group_id: int | None = None,
) -> None:
    """记录命令级审计日志。"""
    from ......database.orm_crud import DatabaseError
    from ......repositories.message_store import record_api_call

    audit_group_id = group_id if group_id is not None else event.group_id
    data_summary = (
        f"operator={event.user_id}, target={target_user_id}, "
        f"action={action}, group={audit_group_id}"
    )
    if duration is not None:
        data_summary += f", duration={duration}"
    if reason is not None:
        data_summary += f", reason={reason}"

    try:
        await record_api_call(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            protocol_id=None,
            bot_id=bot_id(bot),
            api_name=f"command:{action}",
            data_summary=data_summary,
            result_summary="success",
            exception_summary=None,
            audit_type="command",
        )
    except DatabaseError:
        logger.exception(f"记录命令审计失败: action={action}")


def format_user_display_name(
    target_user_id: int,
    target_name: str | None,
    *,
    style: str = "at",
) -> str:
    """格式化用户显示名称。

    Args:
        target_user_id: 用户 ID
        target_name: 用户名称（可能为空）
        style: 显示样式，"at" 表示 @名称 格式，"detail" 表示 名称(ID) 格式

    Returns:
        格式化后的用户显示名称
    """
    if style == "at":
        return f"@{target_name}" if target_name else str(target_user_id)
    # detail style
    return f"{target_name}({target_user_id})" if target_name else str(target_user_id)


async def record_audit_fire_and_forget(  # noqa: PLR0913
    bot: Onebot11Bot,
    event: Onebot11GroupMessageEvent,
    *,
    action: str,
    target_user_id: int | None = None,
    reason: str | None = None,
    duration: int | None = None,
) -> None:
    """异步记录审计日志（fire-and-forget 模式）。

    封装 fire_and_forget + record_command_audit 的常用模式。
    """
    from ......core.async_utils import fire_and_forget

    fire_and_forget(
        record_command_audit(
            bot,
            event,
            action=action,
            target_user_id=target_user_id,
            reason=reason,
            duration=duration,
        ),
        name=f"audit:{action}",
    )
