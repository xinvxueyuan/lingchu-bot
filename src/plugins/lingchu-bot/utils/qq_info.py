import requests
import time

API_URL = "https://jkapi.com/api/qqinfo"

def check_qq_valid(qq: str) -> bool:
    """检查QQ号码是否有效
    
    Args:
        qq: 要检查的QQ号码
        
    Returns:
        bool: True表示有效，False表示无效
    """
    try:
        response = requests.get(f"{API_URL}?qq={qq}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("code") == 200 and data.get("nick") is not None
        return False
    except Exception:
        return False

def clean_blacklist_file(file_path: str, batch_size: int = 50) -> None:
    """清理黑名单文件中的无效QQ号码
    
    Args:
        file_path: 黑名单文件路径
        batch_size: 每次批量处理的号码数量
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        qq_list = [line.strip() for line in f if line.strip()]
    
    valid_qqs = []
    invalid_qqs = []
    
    # 分批处理避免请求过于频繁
    for i in range(0, len(qq_list), batch_size):
        batch = qq_list[i:i+batch_size]
        for qq in batch:
            if check_qq_valid(qq):
                valid_qqs.append(qq)
            else:
                invalid_qqs.append(qq)
            time.sleep(1)  # 避免请求过于频繁
        
        print(f"已处理 {min(i+batch_size, len(qq_list))}/{len(qq_list)} 个QQ号")
    
    # 保存有效的QQ号码
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(valid_qqs))
    
    print(f"清理完成，保留 {len(valid_qqs)} 个有效QQ号，删除 {len(invalid_qqs)} 个无效QQ号")
    if invalid_qqs:
        print("删除的无效QQ号:", ', '.join(invalid_qqs))

if __name__ == "__main__":
    blacklist_path = "c:/Users/13305/Documents/dev/lingchu-nonebot-bot/src/plugins/lingchu-bot/data/全局_设置/全局黑名单.ini"
    clean_blacklist_file(blacklist_path)
