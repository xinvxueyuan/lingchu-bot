from nonebot import logger, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot_plugin_alconna.uniseg import UniMessage

from .utils.parse_id import (
    get_display,
    parse_ids_by_cmd,
)
from .utils.tools import check_super_and_owner

# ================= 指令注册 =================
add_admin_cmd = on_startswith("设置管理员", priority=5, block=True)
remove_admin_cmd = on_startswith("取消管理员", priority=5, block=True)


@add_admin_cmd.handle()
async def handle_add_admin(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理设置管理员命令，支持多用户和单用户
    """
    err = await check_super_and_owner(bot, event, "设置管理员")
    if err:
        await UniMessage.text(err).send(reply_to=True)
        return
    user_ids = parse_ids_by_cmd(event.raw_message, ["设置管理员"])
    if not user_ids:
        await UniMessage.text(
            "格式错误，请使用：设置管理员@某人 或 设置管理员[QQ号]"
            "\nTip: 多个请用空格分隔"
        ).send(reply_to=True)
        return
    msg = []
    for uid in user_ids:
        try:
            await bot.set_group_admin(
                group_id=event.group_id, user_id=int(uid), enable=True
            )
            msg.append(f"设置管理员成功: {get_display(uid, event.raw_message)}")
        except ActionFailed as e:
            logger.error(f"设置管理员{uid}失败: {e}")
            msg.append(f"设置管理员失败: {get_display(uid, event.raw_message)}")
    await UniMessage.text("\n".join(msg) if msg else "无用户被设置管理员").send(
        reply_to=True
    )


@remove_admin_cmd.handle()
async def handle_remove_admin(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理取消管理员命令，支持多用户和单用户
    """
    err = await check_super_and_owner(bot, event, "取消管理员")
    if err:
        await UniMessage.text(err).send(reply_to=True)
        return
    user_ids = parse_ids_by_cmd(event.raw_message, ["取消管理员"])
    if not user_ids:
        await UniMessage.text(
            "格式错误，请使用：取消管理员@某人 或 取消管理员[QQ号]"
            "\nTip: 多个请用空格分隔"
        ).send(reply_to=True)
        return
    msg = []
    for uid in user_ids:
        try:
            await bot.set_group_admin(
                group_id=event.group_id, user_id=int(uid), enable=False
            )
            msg.append(f"取消管理员成功: {get_display(uid, event.raw_message)}")
        except ActionFailed as e:
            logger.error(f"取消管理员{uid}失败: {e}")
            msg.append(f"取消管理员失败: {get_display(uid, event.raw_message)}")
    await UniMessage.text("\n".join(msg) if msg else "无用户被取消管理员").send(
        reply_to=True
    )
