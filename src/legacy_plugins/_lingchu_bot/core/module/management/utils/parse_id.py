def parse_cmd_and_args(
    raw_message: str, cmd_keywords: list[str]
) -> tuple[str | None, str]:
    """
    解析命令关键词及其后所有内容。
    返回匹配到的命令关键词和其后所有内容（去除前后空白）。
    例如：
        parse_cmd_and_args("禁言123456 60秒", ["禁言"]) -> ("禁言", "123456 60秒")
    """
    cmd_pattern = "|".join(cmd_keywords)
    match = re.match(rf"({cmd_pattern})(.*)", raw_message)
    if match:
        cmd = match.group(1)
        args = match.group(2).strip()
        return cmd, args
    return None, ""


import re


def parse_ids_by_cmd(raw_message: str, cmd_keywords: list[str]) -> list[str]:
    """
    通用解析命令中的用户id，支持@和纯数字两种格式
    示例: cmd_keywords: ["设置管理员", "禁言", "解禁", "踢", "授予头衔", "剥夺头衔"]
    """
    cmd_pattern = "|".join(cmd_keywords)
    # 兼容 [CQ:at,qq=xxx] 和 [at:qq=xxx]
    pattern_at = rf"(?:{cmd_pattern})((?:\[(?:CQ:)?at,qq=\d+(?:,name=[^\]]+)?\]\s?)+)"
    pattern_plain = rf"(?:{cmd_pattern})\s*((?:\d+\s?)+)"
    match = re.search(pattern_at, raw_message)
    if match:
        at_block = match.group(1).strip()
        return re.findall(r"\[(?:CQ:)?at,qq=(\d+)", at_block)
    match = re.search(pattern_plain, raw_message)
    if match:
        ids_block = match.group(1).strip()
        return [uid for uid in ids_block.split() if uid.isdigit()]
    return []


def get_display(uid: str, raw_message: str) -> str:
    """
    优先返回@name，无name则返回qq号
    """
    # 兼容 [CQ:at,qq=xxx,name=xxx] 和 [at:qq=xxx,name=xxx]
    pattern = rf"\[(?:CQ:)?at,qq={uid}(?:,name=([^\]]+))?\]"
    match = re.search(pattern, raw_message)
    if match and match.group(1):
        return f"@{match.group(1)}"
    if uid:
        return uid
    return ""


def parse_ids_and_time(
    raw_message: str, cmd_keywords: list[str]
) -> tuple[list[str], int | None]:
    """
    解析命令，返回用户id列表和纯数字
    支持格式示例：
    1. 命令[CQ:at,qq=123456,name=xxx] [CQ:at,qq=654321,name=yyy] 60
    2. 命令123456 654321 60
    cmd_keywords: ["禁言", ...]
    """
    _, args = parse_cmd_and_args(raw_message, cmd_keywords)
    match = re.match(r"((?:\[(?:CQ:)?at,qq=\d+(?:,name=[^\]]+)?\]\s?)+)\s*(\d+)", args)
    if match:
        at_block = match.group(1).strip()
        mute_time = int(match.group(2))
        return re.findall(r"\[(?:CQ:)?at,qq=(\d+)", at_block), mute_time
    match = re.match(r"((?:\d+\s?)+)\s*(\d+)", args)
    if match:
        ids_block = match.group(1).strip()
        mute_time = int(match.group(2))
        return [uid for uid in ids_block.split() if uid.isdigit()], mute_time
    return [], None


def parse_ids_and_title(
    raw_message: str, cmd_keywords: list[str]
) -> tuple[list[str], str]:
    """
    解析命令，返回用户id列表和指令内容
    支持格式示例：
    1. 命令[CQ:at,qq=123456,name=xxx] [CQ:at,qq=654321,name=yyy] 头衔内容
    2. 命令123456 654321 头衔内容
    cmd_keywords: ["授予头衔"]
    """
    _, args = parse_cmd_and_args(raw_message, cmd_keywords)
    match = re.match(r"((?:\[(?:CQ:)?at,qq=\d+(?:,name=[^\]]+)?\]\s?)+)\s*(.+)", args)
    if match:
        at_block = match.group(1).strip()
        title = match.group(2).strip()
        return re.findall(r"\[(?:CQ:)?at,qq=(\d+)", at_block), title
    match = re.match(r"((?:\d+\s?)+)\s*(.+)", args)
    if match:
        ids_block = match.group(1).strip()
        title = match.group(2).strip()
        return [uid for uid in ids_block.split() if uid.isdigit()], title
    return [], ""
