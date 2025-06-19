from pathlib import Path
from configparser import ConfigParser
from nonebot.log import logger


def check_qq_auth(qq: str) -> bool:
    """
    检查指定QQ号是否具有管理员权限。

    Args:
        qq (str): 需要检查权限的QQ号。

    Returns:
        bool: 如果QQ号有管理员权限返回 True，否则返回 False。
    """
    # 构建配置文件路径
    config_path = Path(__file__).parent.parent.parent / "data/全局_设置/管理.ini"

    # 检查配置文件是否存在
    if not config_path.is_file():
        logger.warning(f"配置文件不存在: {config_path}")
        return False

    try:
        # 初始化配置解析器并读取配置文件
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")
        # 遍历所有配置节，检查QQ号是否在对应节的QQ字段中
        return any(
            qq in config.get(section, "QQ").strip().split("-")
            for section in config.sections()
            if config.has_option(section, "QQ")
        )
    except Exception as e:
        # 记录检查权限时出现的错误
        logger.error(f"检查QQ权限时出错: {e}", exc_info=True)
        return False
