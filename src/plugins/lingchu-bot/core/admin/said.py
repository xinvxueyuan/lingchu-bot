import re
import asyncio
from typing import Set, Optional, Tuple, Dict, Any, cast
from nonebot import on_command, on_notice, get_bot
from nonebot.adapters.onebot.v11 import (
    Bot as OneBot,  # 导入为 OneBot 以避免混淆
    Message, 
    MessageEvent, 
    GroupMessageEvent, 
    GroupBanNoticeEvent,
    NoticeEvent
)
from nonebot.params import CommandArg
from nonebot.rule import Rule
from nonebot.plugin import PluginMetadata

from ..lib.basic import *
from ..auth.level_validator import check_qq_auth

# 辅助函数：检查事件是否为群聊消息事件
def is_group_message_event(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent)

# 定义规则：检查是否为群聊且发送者有权限
def group_admin_rule(event: MessageEvent) -> bool:
    """检查是否为群聊且发送者是群主/管理员/主人/超管"""
    # 只处理群聊事件
    if not is_group_message_event(event):
        return False
    
    # 获取发送者QQ
    qq = str(event.user_id)
    # 检查用户权限（主人=1，超管=2）
    auth_level = check_qq_auth(qq)
    
    # 如果是主人或超管直接通过
    if auth_level in {1, 2}:
        return True
    
    # 如果是群聊消息事件，检查发送者角色
    if isinstance(event, GroupMessageEvent):
        role = getattr(event.sender, "role", None)
        return role in ["owner", "admin"]
    
    return False

# 组合规则
admin_rule = Rule(is_group_message_event, group_admin_rule)

# 命令处理器
mute = on_command("禁言", aliases={"禁"}, priority=5, block=True, rule=admin_rule)
unmute = on_command("解禁", aliases={"解"}, priority=5, block=True, rule=admin_rule)
mute_all = on_command("全体禁言", aliases={"全部禁言", "全员禁言"}, priority=5, block=True, rule=admin_rule)
unmute_all = on_command("全体解禁", aliases={"全部解禁", "全员解禁"}, priority=5, block=True, rule=admin_rule)

# 监听群禁言事件
ban_monitor = on_notice(priority=10, block=False)

async def is_ban_event(event: NoticeEvent) -> bool:
    """检查是否是群成员禁言事件"""
    if not isinstance(event, GroupBanNoticeEvent):
        return False
    return event.sub_type == "ban" and event.duration > 0

@ban_monitor.handle()
async def ban_event_handler(event: GroupBanNoticeEvent):
    await handle_ban_event(event)

async def parse_targets_and_time(
    message: Message, 
    event: GroupMessageEvent
) -> Tuple[Set[str], Optional[int]]:
    """解析消息中的目标QQ和禁言时间
    支持格式：
    - 禁言 @某人60
    - 禁言 @某人 60
    - 禁言 123456 60
    """
    qqs: Set[str] = set()
    time_arg: Optional[int] = None
    text_segments = []
    
    # 遍历消息段
    for segment in message:
        if segment.type == "at":
            qq = segment.data.get("qq", "")
            # 忽略@全体
            if qq != "all" and qq.isdigit():
                qqs.add(qq)
        elif segment.type == "text":
            text_segments.append(segment.data["text"])
    
    # 合并文本段
    full_text = "".join(text_segments).strip()
    
    # 如果有@目标，则尝试从文本中提取时间
    if qqs and full_text:
        # 尝试提取时间（可能是紧跟在@后面的数字）
        numbers = re.findall(r"\d+", full_text)
        if numbers:
            try:
                time_arg = int(numbers[-1])
            except (ValueError, IndexError):
                pass
    
    # 如果没有@目标，则第一个数字是QQ号，第二个是时间
    elif not qqs and full_text:
        parts = full_text.split()
        if len(parts) >= 1:
            # 第一个部分是QQ号
            if parts[0].isdigit():
                qqs.add(parts[0])
                # 如果有第二个部分，则是时间
                if len(parts) >= 2 and parts[1].isdigit():
                    try:
                        time_arg = int(parts[1])
                    except ValueError:
                        pass
    
    return qqs, time_arg

def is_immune(
    target_qq: str, 
    group_role: Optional[str],
    operator_auth: int
) -> bool:
    """
    检查目标是否免疫禁言（不可被禁言）
    """
    # 检查目标身份
    target_auth = check_qq_auth(target_qq)
    
    # 情况1：目标是主人 → 任何情况都免疫
    if target_auth == 1:
        return True
    
    # 情况2：目标是群主/群管理员 → 免疫
    if group_role in {"owner", "admin"}:
        return True
    
    # 情况3：目标是超管且操作者不是主人 → 免疫
    if target_auth == 2 and operator_auth != 1:
        return True
    
    return False

async def get_group_role(bot: OneBot, group_id: int, user_id: int) -> Optional[str]:
    """获取成员在群内的角色"""
    try:
        member_info = await bot.get_group_member_info(
            group_id=group_id, 
            user_id=user_id,
            no_cache=True
        )
        return member_info.get("role", "member")
    except Exception:
        return None

@mute.handle()
async def handle_mute(
    bot: OneBot,
    event: GroupMessageEvent,
    message: Message = CommandArg(),
):
    """处理禁言命令"""
    # 获取操作者的权限级别
    operator_auth = check_qq_auth(str(event.user_id))
    group_id = event.group_id
    
    # 解析目标和时间
    target_qqs, mute_time = await parse_targets_and_time(message, event)
    if not target_qqs:
        await bot.send(event, "请指定禁言目标（@成员或输入QQ号）")
        return
    
    if mute_time is None or mute_time <= 0:
        await bot.send(event, "禁言时间必须为正整数（秒）")
        return
    
    # 过滤目标
    valid_targets = []
    immune_targets = []
    operator_qq = str(event.user_id)
    
    for target_qq in target_qqs:
        # 跳过操作者自己
        if target_qq == operator_qq:
            immune_targets.append(f"{target_qq}（操作者自己）")
            continue
        
        # 获取目标在群内的角色
        group_role = await get_group_role(bot, group_id, int(target_qq))
        # 目标不在群内
        if group_role is None:
            immune_targets.append(f"{target_qq}（不在本群）")
            continue
        
        # 检查免疫状态
        if is_immune(target_qq, group_role, operator_auth):
            reason = "主人/超管" if group_role == "member" else group_role
            immune_targets.append(f"{target_qq}（{reason}）")
            continue
        
        valid_targets.append(target_qq)
    
    # 执行禁言
    success_targets = []
    for target_qq in valid_targets:
        try:
            await bot.set_group_ban(
                group_id=group_id,
                user_id=int(target_qq),
                duration=mute_time
            )
            success_targets.append(target_qq)
            await asyncio.sleep(1)  # 避免请求过频
        except Exception as e:
            immune_targets.append(f"{target_qq}（禁言失败：{str(e)}）")
    
    # 构造结果消息
    msg = []
    if success_targets:
        msg.append(f"禁言成功（{mute_time}秒）：{', '.join(success_targets)}")
    if immune_targets:
        msg.append("以下成员无法禁言：" + ", ".join(immune_targets))
    
    if msg:
        await bot.send(event, "\n".join(msg))

@unmute.handle()
async def handle_unmute(
    bot: OneBot,
    event: GroupMessageEvent,
    message: Message = CommandArg(),
):
    """处理解禁命令"""
    group_id = event.group_id
    
    # 解析目标（不需要时间）
    target_qqs, _ = await parse_targets_and_time(message, event)
    if not target_qqs:
        await bot.send(event, "请指定解禁目标（@成员或输入QQ号）")
        return
    
    # 执行解禁
    success_targets = []
    fail_targets = []
    
    for target_qq in target_qqs:
        try:
            await bot.set_group_ban(
                group_id=group_id,
                user_id=int(target_qq),
                duration=0
            )
            success_targets.append(target_qq)
            await asyncio.sleep(0.5)  # 避免请求过频
        except Exception:
            fail_targets.append(target_qq)
    
    # 发送结果
    msg = []
    if success_targets:
        msg.append(f"解除禁言成功：{', '.join(success_targets)}")
    if fail_targets:
        msg.append(f"解禁失败：{', '.join(fail_targets)}")
    
    if msg:
        await bot.send(event, "\n".join(msg))

@mute_all.handle()
async def handle_mute_all(
    bot: OneBot,
    event: GroupMessageEvent,
):
    """全体禁言"""
    group_id = event.group_id
    try:
        await bot.set_group_whole_ban(group_id=group_id, enable=True)
        await bot.send(event, "已开启全体禁言")
    except Exception as e:
        await bot.send(event, f"全体禁言失败：{str(e)}")

@unmute_all.handle()
async def handle_unmute_all(
    bot: OneBot,
    event: GroupMessageEvent,
):
    """全体解禁"""
    group_id = event.group_id
    try:
        await bot.set_group_whole_ban(group_id=group_id, enable=False)
        await bot.send(event, "已解除全体禁言")
    except Exception as e:
        await bot.send(event, f"解除全体禁言失败：{str(e)}")

async def handle_ban_event(event: GroupBanNoticeEvent):
    """监听群禁言事件（主人/超管被禁言时立即解禁）"""
    # 获取正确的 bot 实例
    try:
        # 获取通用 bot 对象
        generic_bot = get_bot(str(event.self_id))
        
        # 转换为 OneBot 特定类型
        bot = cast(OneBot, generic_bot)
    except Exception:
        return
    
    # 被禁言用户信息
    user_id = event.user_id
    user_qq = str(user_id)
    group_id = event.group_id
    
    # 检查身份：必须是主人或超管
    if not check_qq_auth(user_qq) in {1, 2}:
        return
    
    # 获取用户在群内的角色
    group_role = await get_group_role(bot, group_id, user_id)
    
    # 如果用户是群主或管理员，不处理（应该不会被禁言，以防万一）
    if group_role in {"owner", "admin"}:
        return
    
    # 操作者信息（执行禁言的人）
    operator_id = event.operator_id
    operator_qq = str(operator_id)
    
    # 尝试获取操作者群名片或昵称
    operator_name = operator_qq
    try:
        operator_info = await bot.get_group_member_info(
            group_id=group_id,
            user_id=operator_id,
            no_cache=True
        )
        operator_name = operator_info.get("card") or operator_info.get("nickname", operator_qq)
    except Exception:
        pass
    
    try:
        # 立即解禁
        await bot.set_group_ban(
            group_id=group_id,
            user_id=user_id,
            duration=0
        )
        
        # 发送警告消息
        msg = (
            f"检测到管理员【{user_qq}】被禁言！\n"
            f"操作者：{operator_name}({operator_qq})\n"
            f"已自动解除禁言，请管理员确认情况！"
        )
        await bot.send_group_msg(group_id=group_id, message=msg)
    except Exception as e:
        # 重要：记录错误但避免阻塞
        pass

# 插件元数据
__plugin_meta__ = PluginMetadata(
    name="群管理",
    description="群管理禁言解禁等功能",
    usage="禁言 @成员 60 [60秒禁言]",
    extra={
        "example": "禁言 @张三 600",
        "notice": "主人/超管不会被禁言"
    }
)