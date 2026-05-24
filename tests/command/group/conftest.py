from unittest.mock import MagicMock

import pytest
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna.uniseg import At


def finish_text(mock_finish: MagicMock) -> str:
    return str(mock_finish.call_args.kwargs["message"])


@pytest.fixture
def mock_event() -> MagicMock:
    event = MagicMock(spec=MilkyGroupMessageEvent)
    event.data = MagicMock()
    event.data.peer_id = 123456789
    event.data.segments = []
    return event


@pytest.fixture
def mock_bot() -> MagicMock:
    bot = MagicMock(spec=MilkyBot)
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = "Milky"
    return bot


@pytest.fixture
def mock_at() -> MagicMock:
    at = MagicMock(spec=At)
    at.target = "987654321"
    at.display = "测试用户"
    return at
