from pathlib import Path
from configparser import ConfigParser
from nonebot.log import logger

_cached_qq_groups = None  # {section: [qq1, qq2, ...]}
_cached_mtime = 0.0

def check_qq_auth(qq: str) -> bool:
    """检查QQ号是否具有管理员权限"""
    global _cached_qq_groups, _cached_mtime
    config_path = Path(__file__).parent.parent.parent / "data/全局_设置/管理.ini"

    if not config_path.is_file():
        logger.warning(f"配置文件不存在: {config_path}")
        _cached_qq_groups = _cached_mtime = None
        return False

    try:
        current_mtime = config_path.stat().st_mtime
        if current_mtime != _cached_mtime or _cached_qq_groups is None:
            config = ConfigParser()
            config.read(config_path, encoding="utf-8")
            
            _cached_qq_groups = {
                section: [q.strip() for q in config.get(section, "QQ").strip().split("-")]
                for section in config.sections()
                if config.has_option(section, "QQ")
            }
            _cached_mtime = current_mtime
            logger.info("检测到配置文件更新，已刷新缓存")

        return any(qq in qq_group for qq_group in _cached_qq_groups.values())

    except Exception as e:
        logger.error(f"权限检查出错: {e}", exc_info=True)
        return False