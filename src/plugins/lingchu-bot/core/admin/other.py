""" 其他操作 """
# 同步群组命令
from nonebot import on_command
from ..lib.groups import update_groups_table
sync_cmd = on_command("同步群组", aliases={"更新群组"}, priority=5)
@sync_cmd.handle()
async def handle_sync_groups() -> None:
    """手动触发群组同步命令"""
    try:
        await sync_cmd.send("正在更新群组数据...")
        await update_groups_table()
        await sync_cmd.send("群组数据同步完成")
    except Exception as e:
        await sync_cmd.send(f"群组同步失败: {e}")

