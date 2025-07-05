"""公告系统"""
from typing import Optional
import asyncio
from ..lib.basic import *
from ..lib.event import admin_rule
from ..lib.management import manage_group_notice, check_bot_admin_status
from ..lib.database import db_operation


# 注册命令处理器
bulletin = on_command(
    "发公告", 
    aliases={"发布公告","群公告"}, 
    priority=5, 
    block=True, 
    rule=admin_rule
)
bulletin_all = on_command(
    "群发公告", 
    aliases={"全局公告","分群公告"}, 
    priority=5, 
    block=True, 
    rule=admin_rule
)

# 并发控制配置
MAX_CONCURRENT = 5  # 最大并发发送数
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

async def send_notice(group_id: int, content: str, image: Optional[str] = None) -> bool:
    """发送单条群公告
    Args:
        group_id: 目标群号
        content: 公告文本内容
        image: 可选图片URL
    Returns:
        bool: 是否发送成功
    """
    async with SEMAPHORE:
        try:
            return await manage_group_notice(group_id, content, image)
        except Exception:
            return False

async def batch_send(group_ids: list[int], content: str, image: Optional[str] = None) -> int:
    """批量发送群公告
    Args:
        group_ids: 目标群号列表
        content: 公告文本内容
        image: 可选图片URL
    Returns:
        int: 成功发送的群数量
    """
    success_count = 0
    for gid in group_ids:
        try:
            if await send_notice(gid, content, image):
                success_count += 1
        except Exception as e:
            logger.error(f"群{gid}公告发送失败: {e}")
            continue
    
    return success_count

async def process_bulletin_content(event: GroupMessageEvent) -> tuple[str, Optional[str]]:
    """处理公告内容，提取文本和图片
    Args:
        event: 群消息事件
    Returns:
        tuple: (公告文本内容, 可选图片URL)
    """
    # 提取消息中的图片
    image_seg = next((seg for seg in event.message if seg.type == "image"), None)
    image_url = image_seg.data.get("url") if image_seg else None
    
    # 获取原始消息文本并去除命令部分
    raw_text = event.get_plaintext().strip()
    
    # 从命令处理器获取所有可能的命令前缀
    command_prefixes = set()
    for cmd in ["发公告", "群发公告"]:
        command_prefixes.add(cmd)
        if cmd == "发公告":
            command_prefixes.update(["发布公告", "群公告"])
        elif cmd == "群发公告":
            command_prefixes.update(["全局公告", "分群公告"])
    
    # 去除命令前缀
    for prefix in sorted(command_prefixes, key=len, reverse=True):
        if raw_text.startswith(prefix):
            raw_text = raw_text[len(prefix):].strip()
            break
    
    # 构建最终公告内容
    content = raw_text
    
    return content, image_url

async def send_bulletin(event: GroupMessageEvent, matcher: Matcher, all_groups: bool = False) -> None:
    """处理公告发送逻辑
    Args:
        event: 群消息事件
        matcher: 事件匹配器
        all_groups: 是否发送到所有群组
    """
    # 检查机器人管理员权限
    if not await check_bot_admin_status(event.group_id):
        await matcher.send("机器人无管理员权限，无法发送公告")
        return
    
    # 处理公告内容
    content, image_url = await process_bulletin_content(event)
    if not content and not image_url:
        await matcher.send("公告内容不能为空")
        return

    # 单群发送逻辑
    if not all_groups:
        success = await manage_group_notice(event.group_id, content, image_url)
        await matcher.send("公告发送成功" if success else "公告发送失败")
        return

    # 全群广播逻辑
    db_result = await db_operation(operation_type="query", table_name="groups", columns="id")
    if not isinstance(db_result, list) or not db_result:
        await matcher.send("获取群组列表失败")
        return
    
    success = await batch_send([row[0] for row in db_result], content, image_url)
    await matcher.send(f"公告已发送到 {success}/{len(db_result)} 个群组")

@bulletin.handle()
@bulletin_all.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    """命令入口处理函数"""
    is_all = event.get_plaintext().strip().startswith("群发")
    if msg := await send_bulletin(event, matcher, is_all):
        await matcher.send(msg)