from unittest.mock import MagicMock

import pytest
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna.uniseg import At


def finish_text(mock_finish: MagicMock) -> str:
    """
    从模拟的 `finish` 调用中提取并返回 `message` 参数的字符串表示。
    
    Parameters:
        mock_finish (MagicMock): 表示被调用的 `finish` 的 mock；函数最近一次调用的关键字参数中应包含 `"message"`。
    
    Returns:
        str: 最近一次 `finish` 调用中 `message` 参数的字符串表示。
    """
    return str(mock_finish.call_args.kwargs["message"])


@pytest.fixture
def mock_event() -> MagicMock:
    """
    构造并返回一个用于测试的、符合 MilkyGroupMessageEvent 规格的消息事件模拟对象。
    
    返回值为一个 MagicMock，其 spec 设置为 MilkyGroupMessageEvent，包含 .data 属性：
    - data.peer_id: 123456789
    - data.segments: 空列表
    """
    event = MagicMock(spec=MilkyGroupMessageEvent)
    event.data = MagicMock()
    event.data.peer_id = 123456789
    event.data.segments = []
    return event


@pytest.fixture
def mock_bot() -> MagicMock:
    """
    创建并返回一个用于测试的模拟 MilkyBot 对象。
    
    返回:
        MagicMock: 一个以 MilkyBot 为规范的模拟对象，已配置其 `adapter.get_name()` 返回值为 "Milky"。
    """
    bot = MagicMock(spec=MilkyBot)
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = "Milky"
    return bot


@pytest.fixture
def mock_at() -> MagicMock:
    """
    创建并返回一个符合 At 规格的模拟（MagicMock），表示一个提及对象。
    
    返回:
        MagicMock: 一个模拟的 `At` 对象，包含属性 `target`（"987654321"）和 `display`（"测试用户"）。
    """
    at = MagicMock(spec=At)
    at.target = "987654321"
    at.display = "测试用户"
    return at
