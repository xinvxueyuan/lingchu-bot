import os
from configparser import ConfigParser
from pathlib import Path

def check_qq_auth(qq: str) -> int:
    """
    检查传入的QQ号是否在管理设置.ini中存在
    返回:
        0: 不存在
        1: 主人QQ
        2: 超管QQ
    """
    # 构建配置文件路径
    config_path = Path(__file__).parent.parent.parent.parent / "data" / "全局_设置" / "管理设置.ini"
    
    if not config_path.exists():
        return 0
    
    config = ConfigParser()
    config.read(config_path, encoding='utf-8')
    
    # 检查主人QQ
    if config.has_option('主人QQ', 'QQ'):
        owner_qq = config.get('主人QQ', 'QQ').strip('-')
        if qq == owner_qq:
            return 1
    
    # 检查超管QQ
    if config.has_option('超管QQ', 'QQ'):
        super_qqs = config.get('超管QQ', 'QQ').split('-')
        if qq in super_qqs:
            return 2
    
    return 0