from pathlib import Path
from configparser import ConfigParser
from nonebot.log import logger

def check_qq_auth(qq: str) -> bool:
    """检查QQ号权限
    返回:
        True: 有管理员权限
        False: 无权限
    """
    config_path = Path(__file__).parent.parent.parent / "data/全局_设置/管理.ini"
    
    if not config_path.is_file():
        logger.warning(f"配置文件不存在: {config_path}")
        return False
    
    try:
        config = ConfigParser()
        config.read(config_path, encoding='utf-8')
        return any(
            qq in config.get(section, 'QQ').strip().split('-')
            for section in config.sections()
            if config.has_option(section, 'QQ')
        )
    except Exception as e:
        logger.error(f"检查QQ权限时出错: {e}", exc_info=True)
        return False
print(check_qq_auth("2913400124"))  # 测试用例，替换为实际QQ号进行测试