"""Remote management handlers for OneBot V11 adapter."""

from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import At
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ......core.runtime_config import get_handle_config_manager
from ......database.orm_crud import DatabaseError
from ......i18n import _async as _
from ......repositories.blocklist import (
    find_active_block,
    remove_block,
)
from ....commands.announcement import _resolve_image_path
from ....commands.common import selected_adapter_handle
from ....commands.remote import (
    remote_announcement_cmd,
    remote_block_cmd,
    remote_kick_cmd,
    remote_mute_cmd,
    remote_unblock_cmd,
    remote_unmute_cmd,
    remote_whole_mute_cmd,
    remote_whole_unmute_cmd,
)
from .announcement import send_onebot11_group_announcement_notice
from .common import (
    MUTE_DURATION_MAX,
    MUTE_DURATION_MIN,
    ONEBOT_V11_ADAPTER_ID,
    QQ_PLATFORM_ID,
    CommandAudit,
    bot_id,
    check_bot_privilege,
    check_self_target,
    default_admin_reason,
    default_block_reason,
    format_user_display_name,
    record_audit_fire_and_forget,
    resolve_user_onebot11,
    store_block_record,
)


async def _resolve_group_id(
    bot: OneBot11Bot,
    group_id: int | str,
    cmd_matcher: Any,
) -> int | None:
    """解析群聊标识符为群号。

    如果 group_id 是 int 则直接返回。
    如果是 str 且无法转为 int，则模糊匹配群名称。
    匹配失败时调用 cmd_matcher.finish 并返回 None。
    """
    if isinstance(group_id, int):
        return group_id

    # 尝试将纯数字字符串转为 int
    try:
        return int(group_id)
    except (ValueError, TypeError):
        pass

    # 模糊匹配群名称
    try:
        group_list = await bot.get_group_list()
    except OneBot11ActionFailed:
        await cmd_matcher.finish(await _("获取群列表失败"))
        return None

    # 精确匹配优先
    for g in group_list:
        if g.get("group_name") == group_id:
            return g["group_id"]

    # 模糊匹配（包含关系）
    candidates = [g for g in group_list if group_id in g.get("group_name", "")]

    if len(candidates) == 1:
        return candidates[0]["group_id"]

    if len(candidates) > 1:
        names = ", ".join(f"{g['group_name']}({g['group_id']})" for g in candidates[:5])
        await cmd_matcher.finish(
            (await _("匹配到多个群聊，请提供更精确的名称或群号: {names}")).format(
                names=names
            )
        )
        return None

    await cmd_matcher.finish(
        (await _("未找到名称包含「{name}」的群聊")).format(name=group_id)
    )
    return None


async def _check_bot_in_group(bot: OneBot11Bot, group_id: int) -> bool:
    """检查机器人是否在目标群聊中"""
    try:
        group_list = await bot.get_group_list()
        return any(g["group_id"] == group_id for g in group_list)
    except (OneBot11ActionFailed, KeyError, TypeError):
        return False


async def _check_user_in_group(bot: OneBot11Bot, group_id: int, user_id: int) -> bool:
    """检查目标用户是否在目标群聊中"""
    try:
        await bot.get_group_member_info(group_id=group_id, user_id=user_id)
    except OneBot11ActionFailed:
        return False
    else:
        return True


async def _kick_remote_user(
    bot: OneBot11Bot,
    group_id: int,
    user_id: int,
) -> None:
    """踢出远程群用户"""
    await bot.set_group_kick(
        group_id=group_id,
        user_id=user_id,
        reject_add_request=False,
    )


async def _validate_remote_context(
    bot: OneBot11Bot,
    group_id_int: int,
    cmd_matcher: Any,
    *,
    check_admin: bool = True,
) -> bool:
    """验证远程操作的上下文（机器人在群中且有权限）"""
    if not await _check_bot_in_group(bot, group_id_int):
        await cmd_matcher.finish(await _("机器人不在目标群聊中"))
        return False

    if check_admin and not await check_bot_privilege(  # noqa: SIM103
        bot, group_id_int, cmd_matcher
    ):
        return False

    return True


async def _resolve_and_validate_user(
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    group_id_int: int,
    cmd_matcher: Any,
) -> tuple[int, str] | None:
    """解析并验证用户"""
    try:
        target_user_id, target_name = await resolve_user_onebot11(user, bot, event)
    except ValueError as e:
        logger.warning(f"解析用户失败: {e}")
        await cmd_matcher.finish(str(e))
        return None

    if not await _check_user_in_group(bot, group_id_int, target_user_id):
        await cmd_matcher.finish(await _("目标用户不在目标群聊中"))
        return None

    return target_user_id, target_name


@selected_adapter_handle(remote_mute_cmd, "~onebot.v11", "remote_mute")
async def onebot11_remote_mute(  # noqa: PLR0913
    group_id: int | str,
    user: At | int,
    duration: int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    """远程禁言处理器"""
    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_mute_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 参数合法性检查
    if duration < MUTE_DURATION_MIN:
        return await remote_mute_cmd.finish(
            (await _("禁言时长不能小于 {min} 秒")).format(min=MUTE_DURATION_MIN)
        )
    if duration > MUTE_DURATION_MAX:
        return await remote_mute_cmd.finish(
            (await _("禁言时长不能超过 {max} 秒（30天）")).format(max=MUTE_DURATION_MAX)
        )

    # 3. 验证上下文
    if not await _validate_remote_context(bot, group_id_int, remote_mute_cmd):
        return None

    # 4. 解析并验证用户
    user_result = await _resolve_and_validate_user(
        user, bot, event, group_id_int, remote_mute_cmd
    )
    if user_result is None:
        return None
    target_user_id, target_name = user_result

    # 5. 边界条件检查
    if not await check_self_target(target_user_id, bot, event, remote_mute_cmd, "禁言"):
        return None

    # 6. 执行禁言操作
    try:
        await bot.set_group_ban(
            group_id=group_id_int, user_id=target_user_id, duration=duration
        )
    except OneBot11ActionFailed as e:
        logger.error(f"远程禁言失败，操作被拒绝: {e!r}")
        return await remote_mute_cmd.finish(await _("远程禁言失败，操作被拒绝"))

    # 7. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="remote_mute",
            target_user_id=target_user_id,
            duration=duration,
            reason=reason,
            group_id=group_id_int,
        ),
    )

    # 8. 格式化反馈消息
    reason_text = await default_block_reason(reason)
    name_display = format_user_display_name(target_user_id, target_name)
    message = await _(
        "已远程禁言: \n"
        "目标群: {group_id}\n"
        "名称: {name_display}\n"
        "时长: {duration} 秒\n"
        "原因: {reason}\n"
        "标识: {target_user_id}"
    )
    return await remote_mute_cmd.finish(
        message.format(
            group_id=group_id_int,
            name_display=name_display,
            duration=duration,
            reason=reason_text,
            target_user_id=target_user_id,
        )
    )


@selected_adapter_handle(remote_unmute_cmd, "~onebot.v11", "remote_unmute")
async def onebot11_remote_unmute(
    group_id: int | str,
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    """远程解禁处理器"""
    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_unmute_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 验证上下文
    if not await _validate_remote_context(bot, group_id_int, remote_unmute_cmd):
        return None

    # 3. 解析并验证用户
    user_result = await _resolve_and_validate_user(
        user, bot, event, group_id_int, remote_unmute_cmd
    )
    if user_result is None:
        return None
    target_user_id, target_name = user_result

    # 4. 边界条件检查
    if not await check_self_target(
        target_user_id, bot, event, remote_unmute_cmd, "解禁"
    ):
        return None

    # 5. 执行解禁操作
    try:
        await bot.set_group_ban(
            group_id=group_id_int, user_id=target_user_id, duration=0
        )
    except OneBot11ActionFailed as e:
        logger.error(f"远程解禁失败，操作被拒绝: {e!r}")
        return await remote_unmute_cmd.finish(await _("远程解禁失败，操作被拒绝"))

    # 6. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="remote_unmute",
            target_user_id=target_user_id,
            reason=reason,
            group_id=group_id_int,
        ),
    )

    # 7. 格式化反馈消息
    reason_text = await default_admin_reason(reason)
    name_display = format_user_display_name(target_user_id, target_name)
    message = await _(
        "已远程解禁: \n"
        "目标群: {group_id}\n"
        "名称: {name_display}\n"
        "原因: {reason}\n"
        "标识: {target_user_id}"
    )
    return await remote_unmute_cmd.finish(
        message.format(
            group_id=group_id_int,
            name_display=name_display,
            reason=reason_text,
            target_user_id=target_user_id,
        )
    )


@selected_adapter_handle(
    remote_whole_mute_cmd,
    "~onebot.v11",
    "remote_whole_mute",
)
async def onebot11_remote_whole_mute(
    group_id: int | str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    """远程全体禁言处理器"""
    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_whole_mute_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 验证上下文
    if not await _validate_remote_context(bot, group_id_int, remote_whole_mute_cmd):
        return None

    # 3. 执行全体禁言操作
    try:
        await bot.set_group_whole_ban(group_id=group_id_int, enable=True)
    except OneBot11ActionFailed as e:
        logger.error(f"远程全体禁言失败，操作被拒绝: {e!r}")
        return await remote_whole_mute_cmd.finish(
            await _("远程全体禁言失败，操作被拒绝")
        )

    # 4. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(action="remote_whole_mute", group_id=group_id_int),
    )

    return await remote_whole_mute_cmd.finish(
        (await _("已远程开启全体禁言: 目标群 {group_id}")).format(group_id=group_id_int)
    )


@selected_adapter_handle(
    remote_whole_unmute_cmd,
    "~onebot.v11",
    "remote_whole_unmute",
)
async def onebot11_remote_whole_unmute(
    group_id: int | str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    """远程全体解禁处理器"""
    # 检查功能是否启用（全体解禁共用remote_mute配置）
    config = get_handle_config_manager().get_config("remote_mute")
    if not config.enabled:
        return await remote_whole_unmute_cmd.finish(await _("该功能已禁用"))

    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_whole_unmute_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 验证上下文
    if not await _validate_remote_context(bot, group_id_int, remote_whole_unmute_cmd):
        return None

    # 3. 执行全体解禁操作
    try:
        await bot.set_group_whole_ban(group_id=group_id_int, enable=False)
    except OneBot11ActionFailed as e:
        logger.error(f"远程全体解禁失败，操作被拒绝: {e!r}")
        return await remote_whole_unmute_cmd.finish(
            await _("远程全体解禁失败，操作被拒绝")
        )

    # 4. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(action="remote_whole_unmute", group_id=group_id_int),
    )

    return await remote_whole_unmute_cmd.finish(
        (await _("已远程关闭全体禁言: 目标群 {group_id}")).format(group_id=group_id_int)
    )


@selected_adapter_handle(remote_kick_cmd, "~onebot.v11", "remote_kick")
async def onebot11_remote_kick(
    group_id: int | str,
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    """远程踢出群成员处理器"""
    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_kick_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 验证上下文
    if not await _validate_remote_context(bot, group_id_int, remote_kick_cmd):
        return None

    # 3. 解析并验证用户
    user_result = await _resolve_and_validate_user(
        user, bot, event, group_id_int, remote_kick_cmd
    )
    if user_result is None:
        return None
    target_user_id, target_name = user_result

    # 4. 边界条件检查
    if not await check_self_target(target_user_id, bot, event, remote_kick_cmd, "踢出"):
        return None

    # 5. 检查目标用户是否在黑名单中
    try:
        entry = await find_active_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=bot_id(bot),
            group_id=group_id_int,
            user_id=target_user_id,
        )
    except DatabaseError as error:
        logger.error(f"查询黑名单失败，数据库异常: {error!r}")
        return await remote_kick_cmd.finish(await _("查询黑名单失败，数据库异常"))

    if entry is None:
        display_name = format_user_display_name(target_user_id, target_name)
        message = await _("用户 {name} 不在黑名单中，无法执行踢出操作")
        return await remote_kick_cmd.finish(message.format(name=display_name))

    # 6. 执行踢出操作
    try:
        await bot.set_group_kick(
            group_id=group_id_int,
            user_id=target_user_id,
            reject_add_request=False,
        )
    except OneBot11ActionFailed as e:
        logger.error(f"远程踢出群成员失败: {e!r}")
        return await remote_kick_cmd.finish(await _("远程踢出群成员失败，操作被拒绝"))

    # 7. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="remote_kick",
            target_user_id=target_user_id,
            reason=reason,
            group_id=group_id_int,
        ),
    )

    # 8. 反馈结果
    display_name = format_user_display_name(target_user_id, target_name)
    reason_text = f"，原因: {reason}" if reason else ""
    message = await _("已远程踢出群成员 {name}{reason}，目标群: {group_id}")
    return await remote_kick_cmd.finish(
        message.format(name=display_name, reason=reason_text, group_id=group_id_int)
    )


@selected_adapter_handle(remote_block_cmd, "~onebot.v11", "remote_block")
async def onebot11_remote_block(  # noqa: PLR0913
    group_id: int | str,
    user: At | int,
    duration: int | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    """远程拉黑群成员处理器"""
    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_block_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 验证上下文
    if not await _validate_remote_context(bot, group_id_int, remote_block_cmd):
        return None

    # 3. 解析并验证用户
    user_result = await _resolve_and_validate_user(
        user, bot, event, group_id_int, remote_block_cmd
    )
    if user_result is None:
        return None
    target_user_id, target_name = user_result

    # 4. 存储黑名单记录并踢出用户
    reason_text = await default_block_reason(reason)
    try:
        await store_block_record(
            scope="group",
            group_id=group_id_int,
            user_id=target_user_id,
            duration=duration,
            reason=reason_text,
            bot=bot,
            operator_id=event.user_id,
        )
        await _kick_remote_user(bot, group_id_int, target_user_id)
    except DatabaseError as error:
        logger.error(f"远程拉黑失败，数据库异常: {error!r}")
        return await remote_block_cmd.finish(await _("远程拉黑失败，数据库异常"))
    except OneBot11ActionFailed as error:
        logger.error(f"远程拉黑失败，操作被拒绝: {error!r}")
        return await remote_block_cmd.finish(await _("远程拉黑失败，操作被拒绝"))

    # 5. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="remote_block",
            target_user_id=target_user_id,
            duration=duration,
            reason=reason,
            group_id=group_id_int,
        ),
    )

    # 6. 格式化反馈消息
    duration_text = await _("永久") if duration is None else f"{duration} 秒"
    name_display = format_user_display_name(target_user_id, target_name)
    message = (
        await _(
            "已远程拉黑并踢出: \n"
            "目标群: {group_id}\n"
            "名称: {name_display}\n"
            "时长: {duration}\n"
            "原因: {reason}\n"
            "标识: {target_user_id}"
        )
    ).format(
        group_id=group_id_int,
        name_display=name_display,
        duration=duration_text,
        reason=reason_text,
        target_user_id=target_user_id,
    )
    logger.info(message)
    return await remote_block_cmd.finish(message=message)


@selected_adapter_handle(remote_unblock_cmd, "~onebot.v11", "remote_unblock")
async def onebot11_remote_unblock(
    group_id: int | str,
    user: At | int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    """远程删黑处理器"""
    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_unblock_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 验证机器人是否在目标群聊中
    if not await _check_bot_in_group(bot, group_id_int):
        return await remote_unblock_cmd.finish(await _("机器人不在目标群聊中"))

    # 3. 解析用户
    try:
        target_user_id, target_name = await resolve_user_onebot11(user, bot, event)
    except ValueError as e:
        logger.warning(f"解析用户失败: {e}")
        return await remote_unblock_cmd.finish(str(e))

    # 4. 删除黑名单记录
    reason_text = await default_admin_reason(reason)
    try:
        result = await remove_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=bot_id(bot),
            scope="group",
            group_id=group_id_int,
            user_id=target_user_id,
        )
        deleted = result[0]
    except DatabaseError as error:
        logger.error(f"远程删黑失败，数据库异常: {error!r}")
        return await remote_unblock_cmd.finish(await _("远程删黑失败，数据库异常"))

    # 5. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="remote_unblock",
            target_user_id=target_user_id,
            reason=reason,
            group_id=group_id_int,
        ),
    )

    # 6. 格式化反馈消息
    name_display = format_user_display_name(target_user_id, target_name)
    message = (
        await _(
            "已远程删黑: \n"
            "目标群: {group_id}\n"
            "名称: {name_display}\n"
            "原因: {reason}\n"
            "标识: {target_user_id}\n"
            "删除记录: {deleted}"
        )
    ).format(
        group_id=group_id_int,
        name_display=name_display,
        reason=reason_text,
        target_user_id=target_user_id,
        deleted=deleted,
    )
    logger.info(message)
    return await remote_unblock_cmd.finish(message=message)


@selected_adapter_handle(
    remote_announcement_cmd,
    "~onebot.v11",
    "remote_announcement",
)
async def onebot11_remote_announcement(
    group_id: int | str,
    content: str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    image: UniImage | None = None,
) -> Any:
    """远程公告处理器"""
    # 检查功能是否启用
    config = get_handle_config_manager().get_config("remote_announcement")
    if not config.enabled:
        return await remote_announcement_cmd.finish(await _("该功能已禁用"))

    # 1. 解析群聊标识符
    resolved_group_id = await _resolve_group_id(bot, group_id, remote_announcement_cmd)
    if resolved_group_id is None:
        return None
    group_id_int = resolved_group_id

    # 2. 输入数据清洗：去除首尾空白字符
    content = content.strip()

    # 3. 参数合法性检查
    if not content:
        return await remote_announcement_cmd.finish(await _("群公告内容不能为空"))

    # 4. 验证上下文
    if not await _validate_remote_context(bot, group_id_int, remote_announcement_cmd):
        return None

    # 5. 解析图片路径
    image_path = await _resolve_image_path(image) if image is not None else None

    # 6. 构造目标群事件上下文并执行发送
    try:
        error_msg = await send_onebot11_group_announcement_notice(
            bot=bot,
            event=event,
            group_id=group_id_int,
            content=content,
            image_path=image_path,
        )
        if error_msg is not None:
            return await remote_announcement_cmd.finish(error_msg)
    except OneBot11ActionFailed as e:
        logger.error(f"远程公告失败，操作被拒绝: {e!r}")
        return await remote_announcement_cmd.finish(await _("远程公告失败，操作被拒绝"))

    # 7. 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(action="remote_announcement", group_id=group_id_int),
    )

    # 8. 反馈结果
    return await remote_announcement_cmd.finish(
        (await _("远程公告已发送: 目标群 {group_id}")).format(group_id=group_id_int)
    )
