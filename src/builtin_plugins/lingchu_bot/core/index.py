import nonebot
from nonebot import logger


def check_state() -> bool:
    """检查机器人的状态配置"""
    config = nonebot.get_driver().config
    state = getattr(config, "state", False)
    # 检查state布尔值是否为True
    return state is True


def check_init_and_config() -> bool:
    """机器人初次启动检查和配置"""
    return True


def index_init() -> None:
    """机器人核心启动索引"""
    if check_init_and_config():
        logger.info("未发现配置或配置损坏，使用默认配置")
        from .model import models  # noqa: F401 # 导入数据库模型
    else:
        logger.info("使用用户配置启动灵初")
