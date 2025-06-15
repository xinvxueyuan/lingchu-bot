from nonebot import get_bot
from ..auth.level_validator import check_qq_auth
from ..lib.basic import *


# 定义命令处理器
ban = on_command("禁言", aliases={"禁言"}, permission=GROUP, priority=5, block=True)
unban = on_command("解禁", aliases={"解禁"}, permission=GROUP, priority=5, block=True)
ban_all = on_command("全体禁言", aliases={"全体禁言"}, permission=GROUP, priority=5, block=True)
unban_all = on_command("全体解禁", aliases={"全体解禁"}, permission=GROUP, priority=5, block=True)

async def check_permission(event: GroupMessageEvent) -> bool:
    """检查用户权限
    返回 True 如果用户是:
    - 主人QQ
    - 超管QQ
    - 群管理员
    - 群主
    """
    # 检查是否是主人或超管
    auth_level = check_qq_auth(str(event.user_id))
    if auth_level >= 1:
        return True
    
    # 检查是否是群管理员或群主
    if hasattr(event, 'sender') and hasattr(event.sender, 'role'):
        return event.sender.role in ['admin', 'owner']
    
    return False

@ban.handle()
async def handle_ban(event: GroupMessageEvent, args: Message = CommandArg()):
    if not await check_permission(event):
        await ban.finish("你没有权限执行此操作")
    
    msg = args.extract_plain_text().strip().split()
    if not msg:
        await ban.finish("请指定要禁言的成员，可以@或输入QQ号")
    
    # 解析禁言时长（默认为60秒）
    duration = 60
    if len(msg) > 1 and msg[-1].isdigit():
        duration = min(int(msg[-1]), 2592000)  # 最长30天
        msg = msg[:-1]
    
    target = msg[0]
    
    # 处理@的情况
    if target.startswith("[CQ:at,qq="):
        qq = target[10:-1]
    elif target.isdigit():
        qq = target
    else:
        await ban.finish("请指定有效的QQ号或@成员")
    
    try:
        bot = get_bot()
        await bot.set_group_ban(
            group_id=event.group_id,
            user_id=int(qq),
            duration=duration
        )
        await ban.finish(f"已禁言成员 {qq}，时长 {duration} 秒")
    except Exception as e:
        await ban.finish(f"禁言失败: {str(e)}")

@unban.handle()
async def handle_unban(event: GroupMessageEvent, args: Message = CommandArg()):
    if not await check_permission(event):
        await unban.finish("你没有权限执行此操作")
    
    msg = args.extract_plain_text().strip().split()
    if not msg:
        await unban.finish("请指定要解禁的成员，可以@或输入QQ号")
    
    target = msg[0]
    
    # 处理@的情况
    if target.startswith("[CQ:at,qq="):
        qq = target[10:-1]
    elif target.isdigit():
        qq = target
    else:
        await unban.finish("请指定有效的QQ号或@成员")
    
    try:
        bot = get_bot()
        await bot.set_group_ban(
            group_id=event.group_id,
            user_id=int(qq),
            duration=0  # 0表示解除禁言
        )
        await unban.finish(f"已解除成员 {qq} 的禁言")
    except Exception as e:
        await unban.finish(f"解禁失败: {str(e)}")

@ban_all.handle()
async def handle_ban_all(event: GroupMessageEvent):
    if not await check_permission(event):
        await ban_all.finish("你没有权限执行此操作")
    
    try:
        bot = get_bot()
        await bot.set_group_whole_ban(
            group_id=event.group_id,
            enable=True
        )
        await ban_all.finish("已开启全体禁言")
    except Exception as e:
        await ban_all.finish(f"全体禁言失败: {str(e)}")

@unban_all.handle()
async def handle_unban_all(event: GroupMessageEvent):
    if not await check_permission(event):
        await unban_all.finish("你没有权限执行此操作")
    
    try:
        bot = get_bot()
        await bot.set_group_whole_ban(
            group_id=event.group_id,
            enable=False
        )
        await unban_all.finish("已解除全体禁言")
    except Exception as e:
        await unban_all.finish(f"解除全体禁言失败: {str(e)}")