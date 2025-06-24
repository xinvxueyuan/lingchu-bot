from pathlib import Path
from nonebot.log import logger

_cached_banned_qqs = set()
_cached_mtime = 0.0

def get_ban_path() -> Path:
    """获取黑名单文件路径"""
    return Path(__file__).parent.parent.parent / "data/全局_设置/全局黑名单.ini"

def _update_cache(ban_path: Path) -> bool:
    """更新黑名单缓存"""
    global _cached_banned_qqs, _cached_mtime
    try:
        current_mtime = ban_path.stat().st_mtime
        if current_mtime != _cached_mtime:
            with open(ban_path, "r", encoding="utf-8") as f:
                _cached_banned_qqs = {line.strip() for line in f if line.strip()}
            _cached_mtime = current_mtime
            logger.info("黑名单缓存已更新")
        return True
    except Exception as e:
        logger.error(f"黑名单操作失败: {e}", exc_info=True)
        return False

def _modify_ban_file(qq: str, action: str) -> bool:
    """修改黑名单文件"""
    ban_path = get_ban_path()
    try:
        with open(ban_path, "r+", encoding="utf-8") as f:
            lines = {line.strip() for line in f if line.strip()}
            
            if action == "add" and qq not in lines:
                lines.add(qq)
            elif action == "remove" and qq in lines:
                lines.remove(qq)
            else:
                return False
                
            f.seek(0)
            f.write("\n".join(lines) + "\n")
            f.truncate()
            
            # 更新缓存
            _cached_banned_qqs = lines
            _cached_mtime = ban_path.stat().st_mtime
            return True
    except Exception as e:
        logger.error(f"{action}黑名单失败: {e}", exc_info=True)
        return False

def add_qq_to_ban(qq: str) -> bool:
    """添加QQ号到黑名单"""
    return _modify_ban_file(qq, "add")

def remove_qq_from_ban(qq: str) -> bool:
    """从黑名单中移除QQ号"""
    return _modify_ban_file(qq, "remove")

def check_qq_banned(qq: str) -> bool:
    """检查指定QQ号是否在全局黑名单中"""
    ban_path = get_ban_path()
    if not ban_path.is_file():
        logger.warning(f"黑名单文件不存在: {ban_path}")
        return False
    return _update_cache(ban_path) and qq in _cached_banned_qqs