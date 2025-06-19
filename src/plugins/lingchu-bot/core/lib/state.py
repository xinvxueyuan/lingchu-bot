from ...config import Config
from nonebot import get_plugin_config

def check_plugins_state():
    """
    检查机器人插件的全局状态。

    此函数通过 `get_plugin_config` 方法获取配置实例，
    并从中提取 `plugins_state` 属性的值，用于表示机器人插件的全局状态。

    Returns:
        bool: 机器人插件的全局状态，True 表示开启，False 表示关闭。
    """
    return get_plugin_config(Config).plugins_state

