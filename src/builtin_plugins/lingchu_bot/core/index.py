from nonebot import logger

from .database.model import models
from .web.mount import BaseMount


def check_init_status() -> bool | None:
    """机器人初次启动检查和配置"""
    return None


def index_init() -> None:
    """机器人核心部分启动索引"""
    BaseMount()  # 挂载WebUI
    if check_init_status():
        logger.info("未发现配置或配置损坏，使用默认配置")
    else:
        logger.info("使用用户配置启动灵初")
