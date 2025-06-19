
import configparser,time,os,re

from configparser import ConfigParser

# nonebot2 核心模块
from nonebot import on_message, on_command, on_notice, on_request,get_bot
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.rule import to_me,Rule
from nonebot.plugin import PluginMetadata
from nonebot.permission import SUPERUSER
from nonebot.matcher import Matcher

from nonebot.adapters.onebot.v11 import (
    # 基础消息类型
    Message,
    MessageSegment,
    
    # 事件类型
    GroupMessageEvent,
    PrivateMessageEvent,
    
    # 通知事件
    GroupIncreaseNoticeEvent,    # 群成员增加
    GroupDecreaseNoticeEvent,    # 群成员减少
    GroupAdminNoticeEvent,       # 群管理员变动
    GroupUploadNoticeEvent,      # 群文件上传
    GroupBanNoticeEvent,         # 群禁言
    
    # 请求事件
    FriendRequestEvent,          # 好友请求
    GroupRequestEvent,           # 入群请求
    
    # 其他
    Bot,
    Event,
    MessageEvent,
    NoticeEvent,
    RequestEvent,
    GROUP,
    
    # 辅助类型
    GroupMessageEvent,
    PrivateMessageEvent,
    PokeNotifyEvent,             # 戳一戳
    HonorNotifyEvent,            # 群荣誉变更
    LuckyKingNotifyEvent,        # 群红包运气王
)
