from nonebot.log import logger


def check_init_status() -> bool | None:
    """机器人启动检查和配置"""
    # TODO: 检查逻辑
    try:
        logger.debug("开始载入初始化模块")
        from ..modules import initial as initial
    except Exception as e:  # noqa: BLE001
        logger.error(f"载入初始化模块失败: {e}")
        return None
    return True


def index_init() -> None:
    """机器人核心部分初始化索引"""
    from nonebot import require

    require("nonebot_plugin_localstore")
    import nonebot_plugin_localstore as store

    logger.add(
        store.get_plugin_cache_dir() / "lingchu_bot.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="1 week",
    )
    logger.add(
        store.get_plugin_cache_dir() / "lingchu_bot.error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="1 week",
    )
    match check_init_status():
        case True:
            logger.info("使用用户配置启动")
            try:
                logger.debug("开始载入系统模块")
                from ..modules import system as system

                logger.debug("开始载入管理模块")
                from ..modules import management as management
            except Exception as e:
                logger.error(f"载入模块失败: {e}")
                raise
        case False:
            logger.info("首次使用，正在引导配置\n")
            # from .module.initial import guide as guide
        case None:
            logger.error("配置错误或损坏\n")
