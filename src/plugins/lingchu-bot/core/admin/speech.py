from typing import Set, Optional, Tuple, Dict, Any, cast, Union
from ..lib.basic import *
from ..lib.event import admin_rule, is_ban_event
from ..auth.level_validator import check_qq_auth


# 命令处理器
mute = on_command("禁言", aliases={"禁"}, priority=5, block=True, rule=admin_rule)
unmute = on_command("解禁", aliases={"解"}, priority=5, block=True, rule=admin_rule)
mute_all = on_command("全体禁言", aliases={"全部禁言", "全员禁言"}, priority=5, block=True, rule=admin_rule)
unmute_all = on_command("全体解禁", aliases={"全部解禁", "全员解禁"}, priority=5, block=True, rule=admin_rule)
# 监听群禁言事件
ban_monitor = on_notice(priority=10, block=False, rule=admin_rule)
def check_target_permission(target_qq: int) -> bool:
    """检查目标用户是否有特殊权限
    返回True表示有权限(不能被禁言)，出错时抛出异常"""
    try:
        return check_qq_auth(str(target_qq))
    except Exception as e:
        logger.error(f"检查QQ权限时出错: {e}")
        raise

async def get_member_role(event: GroupMessageEvent, target_qq: int) -> str:
    """获取群成员角色"""
    try:
        bot = get_bot()
        member_info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=target_qq,
            no_cache=True
        )
        return member_info.get("role", "member")
    except Exception:
        return "member"

async def parse_mute_command(event: GroupMessageEvent) -> Tuple[int, int, Union[Message, MessageSegment]]:
    """
    解析禁言命令
    返回: (target_qq, mute_time, error_message)
    """
    # 1. 提取被@的QQ号
    target_qq = None
    for segment in event.message:
        if segment.type == "at" and segment.data.get("qq") != "all":
            try:
                target_qq = int(segment.data["qq"])
                break
            except (ValueError, KeyError):
                continue
    
    if target_qq is None:
        return 0, 0, Message("请使用标准格式：禁言@某人 时间(秒)")

    # 2. 检查目标身份
    target_role = await get_member_role(event, target_qq)
    if target_role in ["owner", "admin"]:
        return 0, 0, Message("不能禁言群主或管理员")
    if check_target_permission(target_qq):
        return 0, 0, Message("无法对特殊权限用户执行禁言操作")
    if target_qq == event.user_id:
        return 0, 0, Message("不能禁言自己")
    if target_qq == event.self_id:
        return 0, 0, Message("不能禁言机器人")

    # 3. 提取禁言时间
    text = event.message.extract_plain_text().strip()
    parts = [p for p in text.split() if p and not p.startswith("@")]
    if not parts:
        return 0, 0, Message("请指定禁言时间（秒）")
    
    try:
        mute_time = int(parts[-1])
    except ValueError:
        return 0, 0, Message("禁言时间必须是数字")
    
    if mute_time <= 0:
        return 0, 0, Message("禁言时间必须大于0秒")
    if mute_time > 30 * 24 * 60 * 60:  # 最多30天
        mute_time = 30 * 24 * 60 * 60

    return target_qq, mute_time, Message()

@mute.handle()
async def handle_mute(
    event: GroupMessageEvent,
    matcher: Matcher,
    args: Message = CommandArg()
):
    # 解析命令
    target_qq, mute_time, error_msg = await parse_mute_command(event)
    
    # 错误处理
    if error_msg and len(error_msg) > 0:
        await matcher.send(error_msg)
        return

    # 执行禁言
    try:
        bot = get_bot()
        await bot.set_group_ban(
            group_id=event.group_id,
            user_id=target_qq,
            duration=mute_time,
        )
        await matcher.send(
            Message([
                MessageSegment.text("已禁言 "),
                MessageSegment.at(target_qq),
                MessageSegment.text(f" {mute_time}秒")
            ])
        )
    except Exception as e:
        await matcher.send(Message(f"禁言失败: {str(e)}"))