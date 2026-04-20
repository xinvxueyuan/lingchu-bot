from nonebot import logger, on_startswith
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    PrivateMessageEvent,
)
from nonebot_plugin_alconna.uniseg import UniMessage

from ...database import client
from ...database.model import models
from ...utils.check import check_role_permission, check_super_permission

feat_status_cmd = on_startswith("开机", priority=1, block=True)
unfeat_status_cmd = on_startswith("关机", priority=1, block=True)


@feat_status_cmd.handle()
async def _(event: GroupMessageEvent | PrivateMessageEvent):
    if isinstance(event, GroupMessageEvent):
        await handle_switch(
            event,
            feat_status=True,
            success_msg="已开机",
            fail_msg="开机失败，请重试或联系管理员",
        )
    elif isinstance(event, PrivateMessageEvent):
        await handle_switch_private(
            event,
            feat_status=True,
            success_msg="已开机",
            fail_msg="开机失败，请重试或联系管理员",
        )


@unfeat_status_cmd.handle()
async def _(event: GroupMessageEvent | PrivateMessageEvent):
    if isinstance(event, GroupMessageEvent):
        await handle_switch(
            event,
            feat_status=False,
            success_msg="已关机",
            fail_msg="关机失败，请重试或联系控制台管理员",
        )
    elif isinstance(event, PrivateMessageEvent):
        await handle_switch_private(
            event,
            feat_status=False,
            success_msg="已关机",
            fail_msg="关机失败，请重试或联系控制台管理员",
        )


async def handle_switch(
    event: GroupMessageEvent, *, feat_status: bool, success_msg: str, fail_msg: str
) -> None:
    if not await check_role_permission(
        event, {"admin", "owner", "super"}, inherit=True
    ):
        return
    result = await client.update(
        model=models.LoginInfo,
        filters={"login_id": event.self_id},
        values={"feat_status": feat_status},
    )
    logger.debug(
        f"{event.self_id}收到系统功能开关指令: {event.raw_message} "
        f"来自用户: {event.user_id}在群: {event.group_id}"
    )
    if result:
        await UniMessage.text(success_msg).send(reply_to=True)
    else:
        await UniMessage.text(fail_msg).send(reply_to=True)


async def handle_switch_private(
    event: PrivateMessageEvent, *, feat_status: bool, success_msg: str, fail_msg: str
) -> None:
    if not await check_super_permission(event):
        return
    result = await client.update(
        model=models.LoginInfo,
        filters={"login_id": event.self_id},
        values={"feat_status": feat_status},
    )
    logger.debug(
        f"{event.self_id}收到系统功能开关指令: {event.raw_message} "
        f"来自用户: {event.user_id} (私聊)"
    )
    if result:
        await UniMessage.text(success_msg).send(reply_to=True)
    else:
        await UniMessage.text(fail_msg).send(reply_to=True)
