import asyncio
import platform

import psutil
from nonebot import get_plugin_config, logger, on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot_plugin_alconna.uniseg import UniMessage

from ....config import Config
from ...utils.check import check_feat_status, check_role_permission

framework_status_cmd = on_startswith(("框架状态", "框架信息"), priority=5, block=True)
system_status_cmd = on_startswith(("机器状态", "机器信息"), priority=5, block=True)


@framework_status_cmd.handle()
async def handle_framework_status(event: GroupMessageEvent) -> None:
    if not await check_role_permission(
        event, {"admin", "owner", "super"}, inherit=True
    ):
        return
    logger.debug(
        f"{event.self_id}收到获取框架信息指令: {event.raw_message} "
        f"来自用户: {event.user_id}在群: {event.group_id}"
    )
    status = await check_feat_status(event.self_id)
    msg = (
        f"====框架信息====\n\n"
        f"状态：{'已启用' if status else '已禁用'}\n"
        f"版本：{get_plugin_config(Config).version}"
    )
    await UniMessage.text(msg).send()


@system_status_cmd.handle()
async def handle_system_status(event: GroupMessageEvent) -> None:
    if not await check_role_permission(
        event, {"admin", "owner", "super"}, inherit=True
    ):
        return
    logger.debug(
        f"{event.self_id}收到获取机器信息指令: {event.raw_message} "
        f"来自用户: {event.user_id}在群: {event.group_id}"
    )
    cpu_percent, mem, disk, boot_time = await asyncio.gather(
        asyncio.to_thread(psutil.cpu_percent, 1),
        asyncio.to_thread(psutil.virtual_memory),
        asyncio.to_thread(psutil.disk_usage, "/"),
        asyncio.to_thread(psutil.boot_time),
    )
    import datetime

    boot_time_str = datetime.datetime.fromtimestamp(
        boot_time, tz=datetime.UTC
    ).strftime("%Y-%m-%d %H:%M:%S")
    system_info = (
        f"====机器信息====\n\n"
        f"系统：{platform.system()} {platform.release()}\n"
        f"节点名称：{platform.node()}\n"
        f"版本：{platform.version()}\n"
        f"机器类型：{platform.machine()}\n"
        f"处理器：{platform.processor()}\n"
        f"开机时间：{boot_time_str}\n"
        f"CPU使用率：{cpu_percent}%\n"
        f"内存使用率：{mem.percent}% "
        f"({mem.used // (1024**2)}MB/{mem.total // (1024**2)}MB)\n"
        f"磁盘使用率：{disk.percent}% "
        f"({disk.used // (1024**3)}GB/{disk.total // (1024**3)}GB)\n"
    )
    await UniMessage.text(system_info).send()
