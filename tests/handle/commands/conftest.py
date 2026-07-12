from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
import pytest


def finish_text(mock_finish: MagicMock) -> str:
    """
    从模拟的 `finish` 调用中提取并返回 `message` 参数的字符串表示。

    Parameters:
        mock_finish (MagicMock): 表示被调用的 `finish` 的 mock；
            函数最近一次调用可能包含 "message" 关键字参数或位置参数。

    Returns:
        str: 最近一次 `finish` 调用中 `message` 参数的字符串表示。
    """
    call_args = mock_finish.call_args
    if "message" in call_args.kwargs:
        return str(call_args.kwargs["message"])
    if call_args.args:
        return str(call_args.args[0])
    return ""


@pytest.fixture
def mock_onebot11_event() -> MagicMock:
    event = MagicMock(spec=OneBot11GroupMessageEvent)
    event.group_id = 123456789
    event.user_id = 111222333
    event.message = []
    return event


@pytest.fixture
def mock_onebot11_bot() -> MagicMock:
    bot = MagicMock(spec=OneBot11Bot)
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = "OneBot V11"
    bot.self_id = "1000"
    bot.get_group_member_info = AsyncMock(return_value={})
    return bot


@pytest.fixture
def mock_at() -> MagicMock:
    """
    创建并返回一个符合 At 规格的模拟（MagicMock），表示一个提及对象。

    返回:
        MagicMock: 一个模拟的 `At` 对象，包含属性 `target`
            （"987654321"）和 `display`（"测试用户"）。
    """
    from nonebot_plugin_alconna.uniseg import At

    at = MagicMock(spec=At)
    at.target = "987654321"
    at.display = "测试用户"
    return at
