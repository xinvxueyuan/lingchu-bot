"""测试远程管理命令 - 边界行为覆盖"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import At

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    remote as remote_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.remote import (
    remote_announcement_cmd,
    remote_block_cmd,
    remote_kick_cmd,
    remote_mute_cmd,
    remote_unblock_cmd,
    remote_unmute_cmd,
    remote_whole_mute_cmd,
    remote_whole_unmute_cmd,
)

# 测试用群 ID 常量
_GROUP_ID_1 = 111111111
_GROUP_ID_2 = 222222222
_GROUP_ID_NONEXIST = 999999999
_TARGET_USER_ID = 555555555

# 通过对象引用访问远程处理器，避免硬编码模块路径
_resolve_group_id = remote_module._resolve_group_id
onebot11_remote_announcement = remote_module.onebot11_remote_announcement
onebot11_remote_block = remote_module.onebot11_remote_block
onebot11_remote_kick = remote_module.onebot11_remote_kick
onebot11_remote_mute = remote_module.onebot11_remote_mute
onebot11_remote_unblock = remote_module.onebot11_remote_unblock
onebot11_remote_unmute = remote_module.onebot11_remote_unmute
onebot11_remote_whole_mute = remote_module.onebot11_remote_whole_mute
onebot11_remote_whole_unmute = remote_module.onebot11_remote_whole_unmute


@pytest.fixture
def mock_bot() -> MagicMock:
    """创建模拟的 Bot 对象。"""
    bot = MagicMock(spec=OneBot11Bot)
    bot.self_id = "123456789"
    bot.get_group_list = AsyncMock()
    bot.get_group_member_info = AsyncMock()
    bot.set_group_ban = AsyncMock()
    bot.set_group_whole_ban = AsyncMock()
    bot.set_group_kick = AsyncMock()
    bot.call_api = AsyncMock()
    bot.get_version_info = AsyncMock()
    return bot


@pytest.fixture
def mock_event() -> MagicMock:
    """创建模拟的群消息事件。"""
    event = MagicMock(spec=OneBot11GroupMessageEvent)
    event.user_id = 987654321
    event.group_id = _GROUP_ID_1
    return event


@pytest.fixture
def mock_group_list() -> list[dict]:
    """创建模拟的群列表。"""
    return [
        {"group_id": _GROUP_ID_1, "group_name": "测试群1", "self_role": "admin"},
        {"group_id": _GROUP_ID_2, "group_name": "测试群2", "self_role": "owner"},
        {"group_id": 333333333, "group_name": "其他群", "self_role": "member"},
    ]


class TestResolveGroupId:
    """测试 _resolve_group_id 函数。"""

    @pytest.mark.asyncio
    async def test_resolve_int_group_id(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        """测试解析整数群 ID。"""
        mock_bot.get_group_list.return_value = mock_group_list
        result = await _resolve_group_id(mock_bot, _GROUP_ID_1, remote_mute_cmd)
        assert result == _GROUP_ID_1

    @pytest.mark.asyncio
    async def test_resolve_numeric_string_group_id(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        """测试解析数字字符串群 ID。"""
        mock_bot.get_group_list.return_value = mock_group_list
        result = await _resolve_group_id(mock_bot, str(_GROUP_ID_2), remote_mute_cmd)
        assert result == _GROUP_ID_2

    @pytest.mark.asyncio
    async def test_resolve_exact_group_name(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        """测试解析精确群名称。"""
        mock_bot.get_group_list.return_value = mock_group_list
        result = await _resolve_group_id(mock_bot, "测试群1", remote_mute_cmd)
        assert result == _GROUP_ID_1

    @pytest.mark.asyncio
    async def test_resolve_fuzzy_group_name(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        """测试模糊匹配群名称（多匹配时 finish）。"""
        mock_bot.get_group_list.return_value = mock_group_list
        with patch.object(
            remote_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await _resolve_group_id(mock_bot, "测试", remote_mute_cmd)
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_multiple_matches(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        """测试多个群匹配时的处理。"""
        mock_bot.get_group_list.return_value = mock_group_list
        with patch.object(
            remote_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await _resolve_group_id(mock_bot, "测试群", remote_mute_cmd)
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_no_match(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        """测试无匹配群时的处理。"""
        mock_bot.get_group_list.return_value = mock_group_list
        with patch.object(
            remote_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await _resolve_group_id(mock_bot, "不存在的群", remote_mute_cmd)
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_get_group_list_failed(self, mock_bot: MagicMock) -> None:
        """测试获取群列表失败时的处理。"""
        mock_bot.get_group_list.side_effect = OneBot11ActionFailed()
        with patch.object(
            remote_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await _resolve_group_id(mock_bot, "任意群名", remote_mute_cmd)
            mock_finish.assert_called_once()


class TestRemoteMute:
    """测试远程禁言命令。"""

    @pytest.mark.asyncio
    async def test_remote_mute_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程禁言。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {"user_id": _TARGET_USER_ID}
        mock_bot.set_group_ban.return_value = {}

        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch.object(remote_mute_cmd, "finish", new_callable=AsyncMock),
        ):
            await onebot11_remote_mute(
                group_id=_GROUP_ID_1,
                user=At("user", str(_TARGET_USER_ID)),
                duration=60,
                bot=mock_bot,
                event=mock_event,
                reason="测试原因",
            )
            mock_bot.set_group_ban.assert_called_once_with(
                group_id=_GROUP_ID_1, user_id=_TARGET_USER_ID, duration=60
            )

    @pytest.mark.asyncio
    async def test_remote_mute_duration_too_short(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试禁言时长过短。"""
        mock_bot.get_group_list.return_value = mock_group_list
        with patch.object(
            remote_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_mute(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    duration=0,
                    bot=mock_bot,
                    event=mock_event,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_mute_duration_too_long(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试禁言时长过长。"""
        mock_bot.get_group_list.return_value = mock_group_list
        with patch.object(
            remote_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_mute(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    duration=31 * 24 * 60 * 60,  # 31 天
                    bot=mock_bot,
                    event=mock_event,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_mute_bot_not_in_group(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
    ) -> None:
        """测试机器人不在目标群聊中。"""
        mock_bot.get_group_list.return_value = []
        with patch.object(
            remote_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_mute(
                    group_id=_GROUP_ID_NONEXIST,
                    user=At("user", str(_TARGET_USER_ID)),
                    duration=60,
                    bot=mock_bot,
                    event=mock_event,
                )
            mock_finish.assert_called_once()


class TestRemoteUnmute:
    """测试远程解禁命令。"""

    @pytest.mark.asyncio
    async def test_remote_unmute_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程解禁。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {"user_id": _TARGET_USER_ID}
        mock_bot.set_group_ban.return_value = {}

        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch.object(remote_unmute_cmd, "finish", new_callable=AsyncMock),
        ):
            await onebot11_remote_unmute(
                group_id=_GROUP_ID_1,
                user=At("user", str(_TARGET_USER_ID)),
                bot=mock_bot,
                event=mock_event,
                reason="测试原因",
            )
            mock_bot.set_group_ban.assert_called_once_with(
                group_id=_GROUP_ID_1, user_id=_TARGET_USER_ID, duration=0
            )


class TestRemoteWholeMute:
    """测试远程全体禁言命令。"""

    @pytest.mark.asyncio
    async def test_remote_whole_mute_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程全体禁言。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.set_group_whole_ban.return_value = {}

        with patch.object(remote_whole_mute_cmd, "finish", new_callable=AsyncMock):
            await onebot11_remote_whole_mute(
                group_id=_GROUP_ID_1,
                bot=mock_bot,
                _event=mock_event,
            )
            mock_bot.set_group_whole_ban.assert_called_once_with(
                group_id=_GROUP_ID_1, enable=True
            )


class TestRemoteWholeUnmute:
    """测试远程全体解禁命令。"""

    @pytest.mark.asyncio
    async def test_remote_whole_unmute_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程全体解禁。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.set_group_whole_ban.return_value = {}

        with patch.object(remote_whole_unmute_cmd, "finish", new_callable=AsyncMock):
            await onebot11_remote_whole_unmute(
                group_id=_GROUP_ID_1,
                bot=mock_bot,
                _event=mock_event,
            )
            mock_bot.set_group_whole_ban.assert_called_once_with(
                group_id=_GROUP_ID_1, enable=False
            )


class TestRemoteKick:
    """测试远程踢出命令。"""

    @pytest.mark.asyncio
    async def test_remote_kick_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程踢出。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {"user_id": _TARGET_USER_ID}
        mock_bot.set_group_kick.return_value = {}

        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.find_active_block",
                new_callable=AsyncMock,
                return_value={"user_id": _TARGET_USER_ID},
            ),
            patch.object(remote_kick_cmd, "finish", new_callable=AsyncMock),
        ):
            await onebot11_remote_kick(
                group_id=_GROUP_ID_1,
                user=At("user", str(_TARGET_USER_ID)),
                bot=mock_bot,
                event=mock_event,
                reason="测试原因",
            )
            mock_bot.set_group_kick.assert_called_once()


class TestRemoteBlock:
    """测试远程拉黑命令。"""

    @pytest.mark.asyncio
    async def test_remote_block_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程拉黑。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {"user_id": _TARGET_USER_ID}
        mock_bot.set_group_kick.return_value = {}

        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.upsert_block",
                new_callable=AsyncMock,
            ),
            patch.object(remote_block_cmd, "finish", new_callable=AsyncMock),
        ):
            await onebot11_remote_block(
                group_id=_GROUP_ID_1,
                user=At("user", str(_TARGET_USER_ID)),
                duration=3600,
                bot=mock_bot,
                event=mock_event,
                reason="测试原因",
            )
            mock_bot.set_group_kick.assert_called_once()


class TestRemoteUnblock:
    """测试远程删黑命令。"""

    @pytest.mark.asyncio
    async def test_remote_unblock_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程删黑。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {"user_id": _TARGET_USER_ID}

        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.remove_block",
                new_callable=AsyncMock,
                return_value=(1,),
            ),
            patch.object(remote_unblock_cmd, "finish", new_callable=AsyncMock),
        ):
            await onebot11_remote_unblock(
                group_id=_GROUP_ID_1,
                user=At("user", str(_TARGET_USER_ID)),
                bot=mock_bot,
                event=mock_event,
                reason="测试原因",
            )


class TestRemoteAnnouncement:
    """测试远程公告命令。"""

    @pytest.mark.asyncio
    async def test_remote_announcement_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试成功的远程公告。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = {
            "data": {
                "protocol_version": "v11",
                "app_version": "4.18.0",
                "app_name": "NapCat.Onebot",
            }
        }
        mock_bot.call_api.return_value = {}

        with patch.object(remote_announcement_cmd, "finish", new_callable=AsyncMock):
            await onebot11_remote_announcement(
                group_id=_GROUP_ID_1,
                content="测试公告内容",
                bot=mock_bot,
                _event=mock_event,
                image=None,
            )
            mock_bot.call_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_announcement_empty_content(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试空内容的远程公告。"""
        mock_bot.get_group_list.return_value = mock_group_list
        with patch.object(
            remote_announcement_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_announcement(
                    group_id=_GROUP_ID_1,
                    content="   ",
                    bot=mock_bot,
                    _event=mock_event,
                    image=None,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_announcement_with_group_name(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
    ) -> None:
        """测试使用群名称而非 ID 的远程公告。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = {
            "data": {
                "protocol_version": "v11",
                "app_version": "4.18.0",
                "app_name": "NapCat.Onebot",
            }
        }
        mock_bot.call_api.return_value = {}

        with patch.object(remote_announcement_cmd, "finish", new_callable=AsyncMock):
            await onebot11_remote_announcement(
                group_id="测试群1",
                content="测试公告内容",
                bot=mock_bot,
                _event=mock_event,
                image=None,
            )
            mock_bot.call_api.assert_called_once()
