"""测试远程管理命令 - 边界行为覆盖"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import At
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    remote as remote_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import (
    announcement as announcement_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.remote import (
    mass_announcement_cmd,
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
onebot11_mass_announcement = remote_module.onebot11_mass_announcement
onebot11_remote_announcement = remote_module.onebot11_remote_announcement
onebot11_remote_block = remote_module.onebot11_remote_block
onebot11_remote_kick = remote_module.onebot11_remote_kick
onebot11_remote_mute = remote_module.onebot11_remote_mute
onebot11_remote_unblock = remote_module.onebot11_remote_unblock
onebot11_remote_unmute = remote_module.onebot11_remote_unmute
onebot11_remote_whole_mute = remote_module.onebot11_remote_whole_mute
onebot11_remote_whole_unmute = remote_module.onebot11_remote_whole_unmute


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for remote handler Depends() injection."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


@pytest.fixture(autouse=True)
def _mock_record_audit_fire_and_forget():
    """避免审计记录触发后台任务和数据库调用。"""
    with patch.object(remote_module, "record_audit_fire_and_forget", new=AsyncMock()):
        yield


@pytest.fixture(autouse=True)
def _mock_find_active_subject_policy():
    """绕过 find_active_subject_policy 的真实 DB 调用。

    remote_mute/remote_kick/remote_block 命令在 protected_subject_feature_keys
    默认列表内，会触发 find_active_subject_policy(session, ...) 的真实查询。
    使用 mock_session 时该查询无法执行，这里将 find_active_subject_policy
    直接 mock 为返回 None（未受保护），让测试聚焦于业务路径。显式测试受保护
    路径的用例可在 with patch(...) 中覆盖此 mock。
    """
    with patch.object(
        remote_module, "find_active_subject_policy", new=AsyncMock(return_value=None)
    ):
        yield


@pytest.fixture
def mock_bot() -> MagicMock:
    """创建模拟的 Bot 对象。"""
    bot = MagicMock(spec=OneBot11Bot)
    bot.self_id = "123456789"
    bot.get_group_list = AsyncMock()
    bot.get_group_member_info = AsyncMock(return_value={"role": "admin"})
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


class TestResolveMassAnnouncementTargets:
    """测试群发公告目标解析。"""

    @pytest.mark.asyncio
    async def test_resolve_blank_targets_defaults_to_all_groups(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list

        result = await remote_module._resolve_mass_announcement_targets(
            mock_bot,
            None,
            mass_announcement_cmd,
        )

        assert result == [_GROUP_ID_1, _GROUP_ID_2, 333333333]

    @pytest.mark.asyncio
    async def test_resolve_target_list_deduplicates_in_order(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list

        result = await remote_module._resolve_mass_announcement_targets(
            mock_bot,
            "111111111，测试群2、111111111",
            mass_announcement_cmd,
        )

        assert result == [_GROUP_ID_1, _GROUP_ID_2]

    @pytest.mark.asyncio
    async def test_resolve_all_targets_from_group_list(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list

        result = await remote_module._resolve_mass_announcement_targets(
            mock_bot,
            "全部群",
            mass_announcement_cmd,
        )

        assert result == [_GROUP_ID_1, _GROUP_ID_2, 333333333]


class TestRemoteMute:
    """测试远程禁言命令。"""

    @pytest.mark.asyncio
    async def test_remote_mute_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        """测试成功的远程禁言。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
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
                session=mock_session,
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
        mock_session: Mock,
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
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_mute_duration_too_long(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
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
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_mute_bot_not_in_group(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_session: Mock,
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
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_mute_rejects_protected_target_in_target_group(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        """远程禁言按目标群校验受保护对象。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        mock_bot.set_group_ban.return_value = {}

        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.find_active_subject_policy",
                new_callable=AsyncMock,
                return_value=object(),
            ),
            patch(
                f"{remote_module.__name__}.operator_is_superuser_onebot11",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch.object(remote_mute_cmd, "finish", new_callable=AsyncMock),
        ):
            await onebot11_remote_mute(
                group_id=_GROUP_ID_1,
                user=At("user", str(_TARGET_USER_ID)),
                duration=60,
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                reason="测试原因",
            )

        mock_bot.set_group_ban.assert_not_called()


class TestRemoteUnmute:
    """测试远程解禁命令。"""

    @pytest.mark.asyncio
    async def test_remote_unmute_success(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        """测试成功的远程解禁。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {
            "role": "admin",
            "user_id": _TARGET_USER_ID,
        }
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
                session=mock_session,
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
        mock_session: Mock,
    ) -> None:
        """测试成功的远程全体禁言。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.set_group_whole_ban.return_value = {}

        with patch.object(remote_whole_mute_cmd, "finish", new_callable=AsyncMock):
            await onebot11_remote_whole_mute(
                group_id=_GROUP_ID_1,
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
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
        mock_session: Mock,
    ) -> None:
        """测试成功的远程全体解禁。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.set_group_whole_ban.return_value = {}

        with patch.object(remote_whole_unmute_cmd, "finish", new_callable=AsyncMock):
            await onebot11_remote_whole_unmute(
                group_id=_GROUP_ID_1,
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
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
        mock_session: Mock,
    ) -> None:
        """测试成功的远程踢出。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
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
                session=mock_session,
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
        mock_session: Mock,
    ) -> None:
        """测试成功的远程拉黑。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        mock_bot.set_group_kick.return_value = {}

        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.store_block_record",
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
                session=mock_session,
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
        mock_session: Mock,
    ) -> None:
        """测试成功的远程删黑。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {
            "role": "admin",
            "user_id": _TARGET_USER_ID,
        }

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
                session=mock_session,
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
        mock_session: Mock,
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
                event=mock_event,
                session=mock_session,
                image=None,
            )
            mock_bot.call_api.assert_called_once_with(
                "_send_group_notice",
                group_id=_GROUP_ID_1,
                content="测试公告内容",
            )

    @pytest.mark.asyncio
    async def test_remote_announcement_empty_content(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
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
                    event=mock_event,
                    session=mock_session,
                    image=None,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_announcement_with_group_name(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
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
                event=mock_event,
                session=mock_session,
                image=None,
            )
            mock_bot.call_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_announcement_uses_protocol_image_path(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """远程公告图片复用公告路径桥接，向 NapCat 传容器内路径。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = {
            "data": {
                "protocol_version": "v11",
                "app_version": "4.18.0",
                "app_name": "NapCat.Onebot",
            }
        }
        mock_bot.call_api.return_value = {}

        host_cache_dir = tmp_path / "napcat-announcement-images"
        fake_config = MagicMock()
        fake_config.cache_dir = tmp_path / "default-cache"
        fake_config.announcement_image_cache_dir = host_cache_dir
        fake_config.announcement_image_protocol_dir = "/lingchu/announcement-images"
        monkeypatch.setattr(announcement_module, "plugin_config", fake_config)

        raw_bytes = b"remote-announcement-image"
        image = MagicMock()
        image.raw = raw_bytes
        image.path = None
        image.url = None

        with patch.object(remote_announcement_cmd, "finish", new_callable=AsyncMock):
            await onebot11_remote_announcement(
                group_id=_GROUP_ID_1,
                content="测试公告内容",
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                image=image,
            )

        expected_md5 = hashlib.md5(raw_bytes).hexdigest()
        mock_bot.call_api.assert_called_once_with(
            "_send_group_notice",
            group_id=_GROUP_ID_1,
            content="测试公告内容",
            image=f"/lingchu/announcement-images/{expected_md5}.png",
        )


class TestMassAnnouncement:
    """测试群发公告命令。"""

    @pytest.mark.asyncio
    async def test_mass_announcement_defaults_to_all_groups(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        """未传目标时默认群发到机器人加入的全部群。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = {
            "data": {
                "protocol_version": "v11",
                "app_version": "4.18.0",
                "app_name": "NapCat.Onebot",
            }
        }
        mock_bot.call_api.return_value = {}

        with patch.object(
            mass_announcement_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            await onebot11_mass_announcement(
                content="测试公告内容",
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                targets=None,
                image=None,
            )

        assert mock_bot.call_api.call_args_list == [
            call("_send_group_notice", group_id=_GROUP_ID_1, content="测试公告内容"),
            call("_send_group_notice", group_id=_GROUP_ID_2, content="测试公告内容"),
            call("_send_group_notice", group_id=333333333, content="测试公告内容"),
        ]
        assert "成功 3 个，失败 0 个" in str(mock_finish.call_args.args[0])

    @pytest.mark.asyncio
    async def test_mass_announcement_sends_to_each_target(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        """显式传多个目标时逐群发送。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = {
            "data": {
                "protocol_version": "v11",
                "app_version": "4.18.0",
                "app_name": "NapCat.Onebot",
            }
        }
        mock_bot.call_api.return_value = {}

        with patch.object(
            mass_announcement_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            await onebot11_mass_announcement(
                content="测试公告内容",
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                targets="111111111,222222222",
                image=None,
            )

        assert mock_bot.call_api.call_args_list == [
            call("_send_group_notice", group_id=_GROUP_ID_1, content="测试公告内容"),
            call("_send_group_notice", group_id=_GROUP_ID_2, content="测试公告内容"),
        ]
        assert "成功 2 个，失败 0 个" in str(mock_finish.call_args.args[0])

    @pytest.mark.asyncio
    async def test_mass_announcement_continues_after_target_failure(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        """单个目标发送失败时继续发送后续目标并汇总失败。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = {
            "data": {
                "protocol_version": "v11",
                "app_version": "4.18.0",
                "app_name": "NapCat.Onebot",
            }
        }
        mock_bot.call_api.side_effect = [OneBot11ActionFailed(), {}]

        with patch.object(
            mass_announcement_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            await onebot11_mass_announcement(
                content="测试公告内容",
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                targets="111111111,222222222",
                image=None,
            )

        assert mock_bot.call_api.call_count == 2
        result_text = str(mock_finish.call_args.args[0])
        assert "成功 1 个，失败 1 个" in result_text
        assert "111111111" in result_text
        assert "222222222" in result_text

    @pytest.mark.asyncio
    async def test_mass_announcement_rejects_empty_content(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        """公告内容为空时直接拒绝。"""
        mock_bot.get_group_list.return_value = mock_group_list

        with patch.object(
            mass_announcement_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_mass_announcement(
                    content="   ",
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                    targets="111111111",
                    image=None,
                )

        assert "群公告内容不能为空" in str(mock_finish.call_args.args[0])

    @pytest.mark.asyncio
    async def test_mass_announcement_uses_one_cached_protocol_image_for_each_group(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """群发公告图片复用公告路径桥接，向每个目标传协议端路径。"""
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = {
            "data": {
                "protocol_version": "v11",
                "app_version": "4.18.0",
                "app_name": "NapCat.Onebot",
            }
        }
        mock_bot.call_api.return_value = {}

        host_cache_dir = tmp_path / "napcat-announcement-images"
        fake_config = MagicMock()
        fake_config.cache_dir = tmp_path / "default-cache"
        fake_config.announcement_image_cache_dir = host_cache_dir
        fake_config.announcement_image_protocol_dir = "/lingchu/announcement-images"
        monkeypatch.setattr(announcement_module, "plugin_config", fake_config)

        raw_bytes = b"mass-announcement-image"
        image = MagicMock()
        image.raw = raw_bytes
        image.path = None
        image.url = None

        with patch.object(mass_announcement_cmd, "finish", new_callable=AsyncMock):
            await onebot11_mass_announcement(
                content="测试公告内容",
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                targets="111111111,222222222",
                image=image,
            )

        expected_md5 = hashlib.md5(raw_bytes).hexdigest()
        assert mock_bot.call_api.call_args_list == [
            call(
                "_send_group_notice",
                group_id=_GROUP_ID_1,
                content="测试公告内容",
                image=f"/lingchu/announcement-images/{expected_md5}.png",
            ),
            call(
                "_send_group_notice",
                group_id=_GROUP_ID_2,
                content="测试公告内容",
                image=f"/lingchu/announcement-images/{expected_md5}.png",
            ),
        ]


class TestResolveGroupIdSingleFuzzy:
    """测试 _resolve_group_id 单候选模糊匹配（覆盖行 107）。"""

    @pytest.mark.asyncio
    async def test_resolve_single_fuzzy_match_returns_group_id(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        """仅匹配到一个群时返回对应群号。"""
        mock_bot.get_group_list.return_value = mock_group_list
        result = await _resolve_group_id(mock_bot, "群1", remote_mute_cmd)
        assert result == _GROUP_ID_1


class TestCheckBotInGroup:
    """测试 _check_bot_in_group 异常分支（覆盖行 129-130）。"""

    @pytest.mark.asyncio
    async def test_returns_false_on_action_failed(self, mock_bot: MagicMock) -> None:
        mock_bot.get_group_list.side_effect = OneBot11ActionFailed()
        assert await remote_module._check_bot_in_group(mock_bot, _GROUP_ID_1) is False

    @pytest.mark.asyncio
    async def test_returns_false_on_key_error(self, mock_bot: MagicMock) -> None:
        mock_bot.get_group_list.return_value = [{"group_name": "无群号键"}]
        assert await remote_module._check_bot_in_group(mock_bot, _GROUP_ID_1) is False

    @pytest.mark.asyncio
    async def test_returns_false_on_type_error(self, mock_bot: MagicMock) -> None:
        mock_bot.get_group_list.return_value = None
        assert await remote_module._check_bot_in_group(mock_bot, _GROUP_ID_1) is False


class TestCheckUserInGroup:
    """测试 _check_user_in_group 异常分支（覆盖行 137-138）。"""

    @pytest.mark.asyncio
    async def test_returns_false_on_action_failed(self, mock_bot: MagicMock) -> None:
        mock_bot.get_group_member_info.side_effect = OneBot11ActionFailed()
        result = await remote_module._check_user_in_group(
            mock_bot, _GROUP_ID_1, _TARGET_USER_ID
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_member_info_succeeds(
        self, mock_bot: MagicMock
    ) -> None:
        mock_bot.get_group_member_info.return_value = {"role": "member"}
        result = await remote_module._check_user_in_group(
            mock_bot, _GROUP_ID_1, _TARGET_USER_ID
        )
        assert result is True


class TestValidateRemoteContext:
    """测试 _validate_remote_context 失败分支（覆盖行 164-166）。"""

    @pytest.mark.asyncio
    async def test_returns_false_when_bot_not_in_group(
        self, mock_bot: MagicMock
    ) -> None:
        mock_bot.get_group_list.return_value = []
        with patch.object(remote_mute_cmd, "finish", new_callable=AsyncMock):
            result = await remote_module._validate_remote_context(
                mock_bot, _GROUP_ID_NONEXIST, remote_mute_cmd
            )
        assert result is False


class TestResolveAndValidateUser:
    """测试 _resolve_and_validate_user 错误分支（覆盖行 183-190）。"""

    @pytest.mark.asyncio
    async def test_returns_none_on_value_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                side_effect=ValueError("无效用户"),
            ),
            patch.object(
                remote_mute_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            result = await remote_module._resolve_and_validate_user(
                At("user", "x"), mock_bot, mock_event, _GROUP_ID_1, remote_mute_cmd
            )
        assert result is None
        mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_in_group(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        mock_bot.get_group_member_info.side_effect = OneBot11ActionFailed()
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch.object(
                remote_mute_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            result = await remote_module._resolve_and_validate_user(
                At("user", str(_TARGET_USER_ID)),
                mock_bot,
                mock_event,
                _GROUP_ID_1,
                remote_mute_cmd,
            )
        assert result is None
        mock_finish.assert_called_once()


class TestIsRemoteProtectedTarget:
    """测试 _is_remote_protected_target（覆盖行 203）。"""

    @pytest.mark.asyncio
    async def test_returns_false_when_command_key_not_protected(
        self, mock_bot: MagicMock, mock_session: Mock
    ) -> None:
        matcher = MagicMock()
        matcher._lingchu_command_key = None
        result = await remote_module._is_remote_protected_target(
            mock_session, mock_bot, _GROUP_ID_1, _TARGET_USER_ID, matcher
        )
        assert result is False


class TestCheckRemoteTargetPrivilege:
    """测试 _check_remote_target_privilege 各分支（覆盖行 224、232-250）。"""

    @pytest.mark.asyncio
    async def test_returns_true_when_protected_and_operator_is_superuser(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        with (
            patch(
                f"{remote_module.__name__}.find_active_subject_policy",
                new_callable=AsyncMock,
                return_value=object(),
            ),
            patch(
                f"{remote_module.__name__}.operator_is_superuser_onebot11",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            result = await remote_module._check_remote_target_privilege(
                mock_session,
                mock_bot,
                mock_event,
                _GROUP_ID_1,
                _TARGET_USER_ID,
                remote_mute_cmd,
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_target_member_info_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        matcher = MagicMock()
        matcher._lingchu_command_key = None
        mock_bot.get_group_member_info.side_effect = OneBot11ActionFailed()
        result = await remote_module._check_remote_target_privilege(
            mock_session, mock_bot, mock_event, _GROUP_ID_1, _TARGET_USER_ID, matcher
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_target_admin_and_operator_can_manage(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        matcher = MagicMock()
        matcher._lingchu_command_key = None
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin"},
            {"role": "owner"},
        ]
        with patch(
            f"{remote_module.__name__}._operator_can_manage_privileged_target",
            return_value=True,
        ):
            result = await remote_module._check_remote_target_privilege(
                mock_session,
                mock_bot,
                mock_event,
                _GROUP_ID_1,
                _TARGET_USER_ID,
                matcher,
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_finishes_when_operator_info_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        matcher = MagicMock()
        matcher._lingchu_command_key = None
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin"},
            OneBot11ActionFailed(),
        ]
        with patch.object(matcher, "finish", new_callable=AsyncMock) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await remote_module._check_remote_target_privilege(
                    mock_session,
                    mock_bot,
                    mock_event,
                    _GROUP_ID_1,
                    _TARGET_USER_ID,
                    matcher,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_finishes_when_operator_cannot_manage_privileged_target(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        matcher = MagicMock()
        matcher._lingchu_command_key = None
        mock_bot.get_group_member_info.side_effect = [
            {"role": "owner"},
            {"role": "member"},
        ]
        with (
            patch(
                f"{remote_module.__name__}._operator_can_manage_privileged_target",
                return_value=False,
            ),
            patch.object(matcher, "finish", new_callable=AsyncMock) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await remote_module._check_remote_target_privilege(
                    mock_session,
                    mock_bot,
                    mock_event,
                    _GROUP_ID_1,
                    _TARGET_USER_ID,
                    matcher,
                )
            mock_finish.assert_called_once()


def _make_disabled_config_manager() -> MagicMock:
    """构造返回 disabled 配置的 HandleConfigManager mock。"""
    fake_config = MagicMock()
    fake_config.enabled = False
    fake_manager = MagicMock()
    fake_manager.get_config = AsyncMock(return_value=fake_config)
    return fake_manager


class TestRemoteMuteActionFailed:
    """测试远程禁言 ActionFailed 分支（覆盖行 305-307）。"""

    @pytest.mark.asyncio
    async def test_remote_mute_action_failed_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        mock_bot.set_group_ban.side_effect = OneBot11ActionFailed()
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch.object(
                remote_mute_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_mute(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    duration=60,
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()


class TestRemoteUnmuteActionFailed:
    """测试远程解禁 ActionFailed 分支（覆盖行 382-384）。"""

    @pytest.mark.asyncio
    async def test_remote_unmute_action_failed_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {
            "role": "admin",
            "user_id": _TARGET_USER_ID,
        }
        mock_bot.set_group_ban.side_effect = OneBot11ActionFailed()
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch.object(
                remote_unmute_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_unmute(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()


class TestRemoteWholeMuteActionFailed:
    """测试远程全体禁言 ActionFailed 分支（覆盖行 442-444）。"""

    @pytest.mark.asyncio
    async def test_remote_whole_mute_action_failed_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.set_group_whole_ban.side_effect = OneBot11ActionFailed()
        with patch.object(
            remote_whole_mute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_whole_mute(
                    group_id=_GROUP_ID_1,
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()


class TestRemoteWholeUnmuteErrorPaths:
    """测试远程全体解禁配置禁用与 ActionFailed 分支（覆盖行 474、489-491）。"""

    @pytest.mark.asyncio
    async def test_remote_whole_unmute_disabled_finishes(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        with (
            patch(
                f"{remote_module.__name__}.get_handle_config_manager",
                return_value=_make_disabled_config_manager(),
            ),
            patch.object(
                remote_whole_unmute_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_whole_unmute(
                    group_id=_GROUP_ID_1,
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_whole_unmute_action_failed_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {"role": "admin"}
        mock_bot.set_group_whole_ban.side_effect = OneBot11ActionFailed()
        with patch.object(
            remote_whole_unmute_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_whole_unmute(
                    group_id=_GROUP_ID_1,
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()


class TestRemoteKickErrorPaths:
    """测试远程踢出错误分支（覆盖行 552-570）。"""

    @pytest.mark.asyncio
    async def test_remote_kick_database_error_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.find_active_block",
                new_callable=AsyncMock,
                side_effect=DatabaseError("db error"),
            ),
            patch.object(
                remote_kick_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_kick(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_kick_entry_none_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.find_active_block",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                remote_kick_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_kick(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_kick_action_failed_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        mock_bot.set_group_kick.side_effect = OneBot11ActionFailed()
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
            patch.object(
                remote_kick_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_kick(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()


class TestRemoteBlockErrorPaths:
    """测试远程拉黑错误分支（覆盖行 639-644）。"""

    @pytest.mark.asyncio
    async def test_remote_block_database_error_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.store_block_record",
                new_callable=AsyncMock,
                side_effect=DatabaseError("db error"),
            ),
            patch.object(
                remote_block_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_block(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    duration=3600,
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_block_action_failed_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = [
            {"role": "admin", "user_id": int(mock_bot.self_id)},
            {"role": "member", "user_id": _TARGET_USER_ID},
            {"role": "member", "user_id": _TARGET_USER_ID},
        ]
        mock_bot.set_group_kick.side_effect = OneBot11ActionFailed()
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.store_block_record",
                new_callable=AsyncMock,
            ),
            patch.object(
                remote_block_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_block(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    duration=3600,
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()


class TestRemoteUnblockErrorPaths:
    """测试远程删黑错误分支（覆盖行 699、704-706、720-722）。"""

    @pytest.mark.asyncio
    async def test_remote_unblock_bot_not_in_group_finishes(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        mock_bot.get_group_list.return_value = []
        with patch.object(
            remote_unblock_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_unblock(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_unblock_value_error_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                side_effect=ValueError("无效用户"),
            ),
            patch.object(
                remote_unblock_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_unblock(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_unblock_database_error_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        with (
            patch(
                f"{remote_module.__name__}.resolve_user_onebot11",
                new_callable=AsyncMock,
                return_value=(_TARGET_USER_ID, "测试用户"),
            ),
            patch(
                f"{remote_module.__name__}.remove_block",
                new_callable=AsyncMock,
                side_effect=DatabaseError("db error"),
            ),
            patch.object(
                remote_unblock_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_unblock(
                    group_id=_GROUP_ID_1,
                    user=At("user", str(_TARGET_USER_ID)),
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                )
            mock_finish.assert_called_once()


def _napcat_version_info() -> dict:
    return {
        "data": {
            "protocol_version": "v11",
            "app_version": "4.18.0",
            "app_name": "NapCat.Onebot",
        }
    }


class TestRemoteAnnouncementErrorPaths:
    """测试远程公告错误分支（覆盖行 774、806-809）。"""

    @pytest.mark.asyncio
    async def test_remote_announcement_disabled_finishes(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        with (
            patch(
                f"{remote_module.__name__}.get_handle_config_manager",
                return_value=_make_disabled_config_manager(),
            ),
            patch.object(
                remote_announcement_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_announcement(
                    group_id=_GROUP_ID_1,
                    content="x",
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                    image=None,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_announcement_action_failed_finishes(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = _napcat_version_info()
        with (
            patch(
                f"{remote_module.__name__}.send_onebot11_group_announcement_notice",
                new_callable=AsyncMock,
                side_effect=OneBot11ActionFailed(),
            ),
            patch.object(
                remote_announcement_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_announcement(
                    group_id=_GROUP_ID_1,
                    content="x",
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                    image=None,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_remote_announcement_returns_error_msg_from_notice(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = _napcat_version_info()
        with (
            patch(
                f"{remote_module.__name__}.send_onebot11_group_announcement_notice",
                new_callable=AsyncMock,
                return_value="发送失败",
            ),
            patch.object(
                remote_announcement_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_remote_announcement(
                    group_id=_GROUP_ID_1,
                    content="x",
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                    image=None,
                )
            mock_finish.assert_called_once()


class TestResolveAllGroupIds:
    """测试 _resolve_all_group_ids 错误分支（覆盖行 849-857）。"""

    @pytest.mark.asyncio
    async def test_returns_none_on_action_failed(self, mock_bot: MagicMock) -> None:
        mock_bot.get_group_list.side_effect = OneBot11ActionFailed()
        with patch.object(
            mass_announcement_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await remote_module._resolve_all_group_ids(
                    mock_bot, mass_announcement_cmd
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_group_entry(
        self, mock_bot: MagicMock
    ) -> None:
        mock_bot.get_group_list.return_value = [{"group_name": "无群号键"}]
        with patch.object(
            mass_announcement_cmd, "finish", new_callable=AsyncMock
        ) as mock_finish:
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await remote_module._resolve_all_group_ids(
                    mock_bot, mass_announcement_cmd
                )
            mock_finish.assert_called_once()


class TestCheckMassAnnouncementTargetContext:
    """测试 _check_mass_announcement_target_context 各分支（覆盖行 908、916-921）。"""

    @pytest.mark.asyncio
    async def test_returns_error_when_bot_not_in_group(
        self, mock_bot: MagicMock
    ) -> None:
        mock_bot.get_group_list.return_value = []
        result = await remote_module._check_mass_announcement_target_context(
            mock_bot, _GROUP_ID_1
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_error_when_member_info_fails(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.side_effect = OneBot11ActionFailed()
        result = await remote_module._check_mass_announcement_target_context(
            mock_bot, _GROUP_ID_1
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_error_when_bot_role_is_member(
        self, mock_bot: MagicMock, mock_group_list: list[dict]
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_group_member_info.return_value = {"role": "member"}
        result = await remote_module._check_mass_announcement_target_context(
            mock_bot, _GROUP_ID_1
        )
        assert result is not None


class TestMassAnnouncementErrorPaths:
    """测试群发公告错误分支（覆盖行 941、961-968、990-993）。"""

    @pytest.mark.asyncio
    async def test_mass_announcement_disabled_finishes(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_session: Mock
    ) -> None:
        with (
            patch(
                f"{remote_module.__name__}.get_handle_config_manager",
                return_value=_make_disabled_config_manager(),
            ),
            patch.object(
                mass_announcement_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            mock_finish.side_effect = Exception("finish called")
            with pytest.raises(Exception, match="finish called"):
                await onebot11_mass_announcement(
                    content="x",
                    bot=mock_bot,
                    event=mock_event,
                    session=mock_session,
                    targets=None,
                    image=None,
                )
            mock_finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_mass_announcement_records_context_error_for_target(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = _napcat_version_info()
        with (
            patch.object(
                remote_module,
                "_check_mass_announcement_target_context",
                new_callable=AsyncMock,
                return_value="机器人不在目标群聊中",
            ),
            patch.object(
                mass_announcement_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            await onebot11_mass_announcement(
                content="x",
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                targets="111111111",
                image=None,
            )
        mock_bot.call_api.assert_not_called()
        assert "失败 1 个" in str(mock_finish.call_args.args[0])

    @pytest.mark.asyncio
    async def test_mass_announcement_records_error_msg_from_notice(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_group_list: list[dict],
        mock_session: Mock,
    ) -> None:
        mock_bot.get_group_list.return_value = mock_group_list
        mock_bot.get_version_info.return_value = _napcat_version_info()
        with (
            patch.object(
                remote_module,
                "send_onebot11_group_announcement_notice",
                new_callable=AsyncMock,
                return_value="发送失败",
            ),
            patch.object(
                mass_announcement_cmd, "finish", new_callable=AsyncMock
            ) as mock_finish,
        ):
            await onebot11_mass_announcement(
                content="x",
                bot=mock_bot,
                event=mock_event,
                session=mock_session,
                targets="111111111",
                image=None,
            )
        assert "失败 1 个" in str(mock_finish.call_args.args[0])
