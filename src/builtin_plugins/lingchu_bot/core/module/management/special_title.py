from nonebot import logger, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot_plugin_alconna.uniseg import UniMessage

from .utils import parse_id as parse
from .utils.tools import check_permissions_and_role

# ========== 指令注册 ==========
grant_title_cmd = on_startswith("授予头衔", priority=5, block=True)
revoke_title_cmd = on_startswith("剥夺头衔", priority=5, block=True)


@grant_title_cmd.handle()
async def handle_grant_title(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理授予头衔命令，支持多用户和单用户，格式：授予头衔@某人/QQ号 [头衔内容]
    """
    if not await check_permissions_and_role(bot, event, "授予头衔"):
        return

    user_ids = parse.parse_ids_by_cmd(event.raw_message, ["授予头衔"])
    special_title = parse.parse_ids_and_title(event.raw_message, ["授予头衔"])[1]

    if not user_ids or not special_title or special_title.isdigit():
        await UniMessage.text(
            "格式错误，请使用：授予头衔@某人/QQ号 [头衔内容]\nTip: 多个请用空格分隔"
        ).send(reply_to=True)
        return

    msg = []
    for uid in user_ids:
        try:
            await bot.set_group_special_title(
                group_id=event.group_id, user_id=int(uid), special_title=special_title
            )
            msg.append(
                f"授予头衔成功: {parse.get_display(uid, event.raw_message)}"
                f" → {special_title}"
            )
        except ActionFailed as e:
            logger.error(f"授予头衔{uid}失败: {e}")
            msg.append(f"授予头衔失败: {parse.get_display(uid, event.raw_message)}")
    await UniMessage.text("\n".join(msg) if msg else "无用户被授予头衔").send(
        reply_to=True
    )


@revoke_title_cmd.handle()
async def handle_revoke_title(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理剥夺头衔命令，支持多用户和单用户
    """
    if not await check_permissions_and_role(bot, event, "剥夺头衔"):
        return

    user_ids = parse.parse_ids_by_cmd(event.raw_message, ["剥夺头衔"])
    if not user_ids:
        await UniMessage.text(
            "格式错误，请使用：剥夺头衔@某人 或 剥夺头衔[QQ号]\nTip: 多个请用空格分隔"
        ).send(reply_to=True)
        return

    msg = []
    for uid in user_ids:
        try:
            await bot.set_group_special_title(
                group_id=event.group_id, user_id=int(uid), special_title=""
            )
            msg.append(f"剥夺头衔成功: {parse.get_display(uid, event.raw_message)}")
        except ActionFailed as e:
            logger.error(f"剥夺头衔{uid}失败: {e}")
            msg.append(f"剥夺头衔失败: {parse.get_display(uid, event.raw_message)}")
    await UniMessage.text("\n".join(msg) if msg else "无用户被剥夺头衔").send(
        reply_to=True
    )
