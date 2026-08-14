"""QQ 群禁言通知监听：自动恢复受白名单保护的用户。

OneBot V11 通过 ``GroupBanNoticeEvent`` 上报群禁言/解禁事件。当受保护
（白名单）用户被任一管理员禁言时，Lingchu 自动调用 ``set_group_ban`` 解禁，
使保护不依赖 bot 自身命令拦截。

规则：
- 仅处理 ``sub_type == "ban"`` 且 ``duration > 0`` 的禁言；
- 命中群级或全局保护记录才恢复；
- QQ 全体禁言期间无法单独解禁个人，通过 bot 自身禁言状态探测并跳过；
- 超级用户禁言非同级（非超级用户）的受保护用户时强制生效，不自动恢复；
- 不受"开机/关机"门禁影响，始终生效。
"""

from datetime import UTC, datetime
from typing import Any

from nonebot import logger, on_notice, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupBanNoticeEvent as OneBot11GroupBanNoticeEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot.rule import Rule

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session, get_session

from ......permissions.subject_policy import find_active_subject_policy
from .common import (
    ONEBOT_V11_ADAPTER_ID,
    QQ_PLATFORM_ID,
    bot_id,
    operator_is_superuser_onebot11,
)


def _is_group_ban_notice(event: Any) -> bool:
    """仅匹配群禁言通知；避免 block=True 吞掉 poke 等其他 notice 事件。"""
    return isinstance(event, OneBot11GroupBanNoticeEvent)


# block=True 只对群禁言事件生效：rule 不命中时事件继续传播，
# 不会拦截 poke/加群/退群等其他 notice（2026-08-15 修复 poke 无响应）。
protect_restore_notice = on_notice(
    priority=1, block=True, rule=Rule(_is_group_ban_notice)
)


async def _record_protect_restore_audit(
    bot: OneBot11Bot,
    group_id: int,
    user_id: int,
    operator_id: int,
    duration: int,
) -> None:
    """后台记录"自动解禁受保护用户"审计。

    ``record_audit_fire_and_forget`` 面向群消息事件（operator 取
    ``event.user_id``），而通知事件里 ``event.user_id`` 是被禁言用户，
    操作者是 ``event.operator_id``，因此这里单独写入。
    """
    from ......database.orm_crud import DatabaseError
    from ......repositories.message_store import AuditEvent, record_api_call

    data_summary = (
        f"operator={operator_id}, target={user_id}, "
        f"action=protect_auto_unmute, group={group_id}, "
        f"sub_type=ban, duration={duration}"
    )
    try:
        async with get_session() as session:
            await record_api_call(
                session,
                AuditEvent(
                    platform_id=QQ_PLATFORM_ID,
                    adapter_id=ONEBOT_V11_ADAPTER_ID,
                    protocol_id=None,
                    bot_id=bot_id(bot),
                    api_name="notice:protect_auto_unmute",
                    data_summary=data_summary,
                    result_summary="success",
                    exception_summary=None,
                    audit_type="notice",
                ),
            )
            await session.commit()
    except DatabaseError:
        logger.exception(
            "记录受保护用户自动解禁审计失败: group=%s user=%s", group_id, user_id
        )


def _fire_protect_restore_audit(
    bot: OneBot11Bot,
    group_id: int,
    user_id: int,
    operator_id: int,
    duration: int,
) -> None:
    from ......core.async_utils import fire_and_forget

    fire_and_forget(
        _record_protect_restore_audit(bot, group_id, user_id, operator_id, duration),
        name="audit:protect_auto_unmute",
    )


async def _is_whole_group_muted(bot: OneBot11Bot, group_id: int) -> bool:
    """探测目标群是否处于全体禁言中。

    QQ 全体禁言会禁言除群主外的所有人（含 bot 自己）。通过 bot 自身在该群
    的 ``shut_up_timestamp`` 是否在未来判断。查询失败时保守返回 False，交由
    后续 ``set_group_ban`` 的 API 结果兜底。
    """
    try:
        bot_info = await bot.get_group_member_info(
            group_id=group_id,
            user_id=int(bot.self_id),
            no_cache=True,
        )
    except (OneBot11ActionFailed, ValueError, TypeError):
        return False
    shut_up_timestamp = bot_info.get("shut_up_timestamp", 0)
    try:
        muted_until = int(shut_up_timestamp)
    except (TypeError, ValueError):
        return False
    if muted_until <= 0:
        return False
    return muted_until > datetime.now(UTC).timestamp()


@protect_restore_notice.handle()
async def handle_group_ban_notice(
    bot: OneBot11Bot,
    event: OneBot11GroupBanNoticeEvent,
    session: async_scoped_session,
) -> None:
    """受白名单保护的用户被禁言时自动解禁。"""
    if event.sub_type != "ban" or event.duration <= 0:
        return

    protected = await find_active_subject_policy(
        session,
        policy_type="protected",
        platform_id=QQ_PLATFORM_ID,
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        bot_id=bot_id(bot),
        group_id=event.group_id,
        user_id=event.user_id,
    )
    if protected is None:
        return

    if await _is_whole_group_muted(bot, event.group_id):
        logger.info(
            "全体禁言中，跳过受保护用户自动恢复: group=%s user=%s",
            event.group_id,
            event.user_id,
        )
        return

    operator_super = await operator_is_superuser_onebot11(session, event.operator_id)
    target_super = await operator_is_superuser_onebot11(session, event.user_id)
    if operator_super and not target_super:
        logger.info(
            "超级用户禁言非同级受保护用户，强制生效: group=%s operator=%s target=%s",
            event.group_id,
            event.operator_id,
            event.user_id,
        )
        return

    try:
        await bot.set_group_ban(
            group_id=event.group_id, user_id=event.user_id, duration=0
        )
    except OneBot11ActionFailed as error:
        logger.warning(
            "自动解禁受保护用户失败: group=%s user=%s error=%r",
            event.group_id,
            event.user_id,
            error,
        )
        return

    _fire_protect_restore_audit(
        bot,
        group_id=event.group_id,
        user_id=event.user_id,
        operator_id=event.operator_id,
        duration=event.duration,
    )
    logger.info(
        "已自动解禁受保护用户: group=%s user=%s operator=%s",
        event.group_id,
        event.user_id,
        event.operator_id,
    )


__all__: tuple[Any, ...] = (
    "handle_group_ban_notice",
    "protect_restore_notice",
)
