from pathlib import Path
from configparser import ConfigParser
from nonebot.log import logger

# 新增：缓存配置数据和最后修改时间
_cached_qq_groups = None  # 格式：{section: [qq1, qq2, ...]}
_cached_mtime = 0.0       # 最后修改时间戳


def check_qq_auth(qq: str) -> bool:
    """
    检查指定QQ号是否具有管理员权限。

    Args:
        qq (str): 需要检查权限的QQ号。

    Returns:
        bool: 如果QQ号有管理员权限返回 True，否则返回 False。
    """
    global _cached_qq_groups, _cached_mtime
    # 构建配置文件路径（保持原有逻辑）
    config_path = Path(__file__).parent.parent.parent / "data/全局_设置/管理.ini"

    # 检查配置文件是否存在（保持原有逻辑，但新增缓存清空逻辑）
    if not config_path.is_file():
        logger.warning(f"配置文件不存在: {config_path}")
        _cached_qq_groups = None  # 文件不存在时清空缓存
        _cached_mtime = 0.0
        return False

    try:
        # 获取当前文件最后修改时间
        current_mtime = config_path.stat().st_mtime
    except Exception as e:
        logger.error(f"获取配置文件修改时间失败: {e}", exc_info=True)
        return False

    # 新增：检测文件是否更新（修改时间变化 或 缓存未初始化时重新加载）
    if current_mtime != _cached_mtime or _cached_qq_groups is None:
        try:
            # 初始化配置解析器并读取配置文件（原有逻辑）
            config = ConfigParser()
            config.read(config_path, encoding="utf-8")
            # 解析并缓存所有节的QQ列表
            qq_groups = {}
            for section in config.sections():
                if config.has_option(section, "QQ"):
                    qq_list = config.get(section, "QQ").strip().split("-")
                    qq_groups[section] = [q.strip() for q in qq_list]  # 去除可能的空格
            # 更新缓存
            _cached_qq_groups = qq_groups
            _cached_mtime = current_mtime
            logger.info("检测到配置文件更新，已刷新缓存")
        except Exception as e:
            logger.error(f"重新加载配置文件时出错: {e}", exc_info=True)
            return False

    # 新增：使用缓存数据检查权限（替代原有遍历逻辑）
    return any(qq in qq_group for qq_group in _cached_qq_groups.values())