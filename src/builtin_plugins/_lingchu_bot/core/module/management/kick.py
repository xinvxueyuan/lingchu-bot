from nonebot import on_startswith
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot_plugin_alconna.uniseg import UniMessage

from .utils.parse_id import (
    parse_ids_by_cmd,
)
from .utils.tools import check_permission_and_send_message, process_user_ids

# ================= 指令注册 =================

kick_cmd = on_startswith("踢", priority=5, block=True)

# ================= 事件处理 =================


@kick_cmd.handle()
async def handle_kick(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理踢人命令，支持多用户和单用户
    """
    user_ids = parse_ids_by_cmd(event.raw_message, ["踢"])
    if not user_ids:
        await UniMessage.text(
            "格式错误，请使用：踢@某人 或 踢[QQ号]\nTip: 多个请用空格分隔"
        ).send(reply_to=True)
        return
    if not await check_permission_and_send_message(
        event, {"admin", "owner", "super"}, "权限不足，仅管理员及以上可执行此操作"
    ):
        return
    await process_user_ids(
        event,
        user_ids,
        lambda uid: bot.set_group_kick(
            group_id=event.group_id, user_id=int(uid), reject_add_request=False
        ),
        success_message="踢出成功: {users}",
        failure_message="踢出失败: {users}",
    )
