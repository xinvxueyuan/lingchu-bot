"""全局异常定义。"""


class LingchuBotError(Exception):
    """插件基础异常。"""


class ConfigError(LingchuBotError):
    """配置错误。"""
