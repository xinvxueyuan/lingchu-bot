"""「一键解禁」与「禁言列表」的 handler、中间层分派与审计解析测试。"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from nonebot.adapters.onebot.v11.exception import (
    ActionFailed as OneBot11ActionFailed,
)
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    mute as mute_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.llbot import (
    mute_list as llbot_mute_list,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.llbot.mute_list import (
    MutedMember,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.mute import (
    mute_list_cmd,
    one_click_unmute_cmd,
)

LLBOT_VERSION_INFO = {"app_name": "LLOneBot", "protocol_version": "v11"}


def finish_message(mock_finish: MagicMock) -> object:
    """返回 matcher.finish 收到的 message 参数。"""
    if mock_finish.call_args:
        if "message" in mock_finish.call_args.kwargs:
            return mock_finish.call_args.kwargs["message"]
        if mock_finish.call_args.args:
            return mock_finish.call_args.args[0]
    return ""


def finish_text(mock_finish: MagicMock) -> str:
    """返回 matcher.finish 收到的 message 参数文本。"""
    return str(finish_message(mock_finish))


class _EnabledManager:
    """返回「启用」配置的 HandleConfigManager 替身。"""

    async def get_config(self, command_key: str) -> HandleConfig:
        return HandleConfig(enabled=True, defaults={}, policies={})


class TestOneClickUnmute:
    """「一键解禁」：协议端分派 + 批量解禁 + 一对一回执。"""

    @pytest.fixture(autouse=True)
    def _mock_record_audit_fire_and_forget(self):
        with patch.object(mute_module, "record_audit_fire_and_forget", new=MagicMock()):
            yield

    @pytest.fixture(autouse=True)
    def _mock_check_bot_privilege(self):
        with patch.object(
            mute_module, "check_bot_privilege", new=AsyncMock(return_value=True)
        ):
            yield

    @pytest.fixture(autouse=True)
    def _mock_handle_config_manager(self):
        with patch.object(
            mute_module, "get_handle_config_manager", return_value=_EnabledManager()
        ):
            yield

    @pytest.mark.asyncio
    async def test_one_click_unmute_flow(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """解析协议端 → 取禁言名单 → 逐个解禁 → 一对一报告。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        # 真实契约：适配器已解包 data，call_api 直接返回成员数组
        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=[
                [
                    {"uin": "10001", "nick": "甲"},
                    {"uin": "10002", "nick": "乙"},
                ],
                [],
            ]
        )
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(one_click_unmute_cmd, "finish") as mock_finish:
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        # 现在会调用两次：首次取名单 + 解禁后复查（同样的 action 与群号）
        assert mock_onebot11_bot.call_api.await_count == 2
        for call in mock_onebot11_bot.call_api.await_args_list:
            assert call.args == ("get_group_shut_list",)
            assert call.kwargs == {"group_id": mock_onebot11_event.group_id}
        assert mock_onebot11_bot.set_group_ban.await_count == 2
        text = finish_text(mock_finish)
        assert "甲" in text and "10001" in text
        assert "乙" in text and "10002" in text

    @pytest.mark.asyncio
    async def test_one_click_unmute_lists_failures(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """失败成员必须在 msg 中逐一列出，且带失败标记。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=[
                [
                    {"uin": "10001", "nick": "甲"},
                    {"uin": "10002", "nick": "乙"},
                ],
                [],
            ]
        )
        mock_onebot11_bot.set_group_ban = AsyncMock(
            side_effect=[None, OneBot11ActionFailed()]
        )

        with patch.object(one_click_unmute_cmd, "finish") as mock_finish:
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        text = finish_text(mock_finish)
        # 逐人钉住标记位置：只断言「存在 ❌」会让标记贴错人照样通过
        assert "✅ 甲(10001)" in text, text
        assert "❌ 乙(10002)" in text, text

    @pytest.mark.asyncio
    async def test_one_click_unmute_failure_does_not_stop_later_members(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """中间一个失败，后面的成员仍必须被处理（不中断、不重试）。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=[
                [
                    {"uin": "1", "nick": "甲"},
                    {"uin": "2", "nick": "乙"},
                    {"uin": "3", "nick": "丙"},
                ],
                [],
            ]
        )
        calls: list[int] = []

        async def fake_ban(**kwargs: object) -> None:
            user_id = int(str(kwargs["user_id"]))
            calls.append(user_id)
            if user_id == 2:
                raise OneBot11ActionFailed

        mock_onebot11_bot.set_group_ban = AsyncMock(side_effect=fake_ban)

        with patch.object(one_click_unmute_cmd, "finish"):
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        assert calls == [1, 2, 3]
        assert mock_onebot11_bot.set_group_ban.await_count == 3

    @pytest.mark.asyncio
    async def test_one_click_unmute_empty(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """名单为空时不动 API，回执说明没人被禁言。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(return_value=[])
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(one_click_unmute_cmd, "finish") as mock_finish:
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_onebot11_bot.set_group_ban.assert_not_called()
        assert "没有被禁言" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_one_click_unmute_unsupported_protocol(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """协议端不支持时回可读文案，且不调私有接口、不误报成功。"""
        mock_onebot11_bot.get_version_info = AsyncMock(
            return_value={"app_name": "NapCat.Onebot", "protocol_version": "v11"}
        )
        mock_onebot11_bot.call_api = AsyncMock()
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(one_click_unmute_cmd, "finish") as mock_finish:
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_onebot11_bot.call_api.assert_not_called()
        mock_onebot11_bot.set_group_ban.assert_not_called()
        assert "不支持" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_one_click_unmute_shut_list_error(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """取名单本身失败时报错，不误报「没有人被禁言」。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(side_effect=OneBot11ActionFailed())
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(one_click_unmute_cmd, "finish") as mock_finish:
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_onebot11_bot.set_group_ban.assert_not_called()
        assert "获取禁言名单失败" in finish_text(mock_finish)


class TestResolveShutListAction:
    """中间层分派：default/ 只解析协议端，不直接调私有 action。"""

    @pytest.mark.asyncio
    async def test_resolve_shut_list_action_llbot(self) -> None:
        """协议端为 LLBot 时返回私有实现。"""
        bot = MagicMock()
        bot.get_version_info = AsyncMock(
            return_value={
                "app_name": "LLOneBot",
                "app_version": "8.3.0",
                "protocol_version": "v11",
            }
        )

        action, error = await mute_module._resolve_shut_list_action(bot)

        assert error is None
        assert action is llbot_mute_list.fetch_group_shut_list

    @pytest.mark.asyncio
    async def test_resolve_shut_list_action_unsupported(self) -> None:
        """未知协议端返回 (None, 提示文案)，不猜实现。"""
        bot = MagicMock()
        bot.get_version_info = AsyncMock(
            return_value={
                "app_name": "NapCat.Onebot",
                "app_version": "4.18.0",
                "protocol_version": "v11",
            }
        )

        action, error = await mute_module._resolve_shut_list_action(bot)

        assert action is None
        assert error

    @pytest.mark.asyncio
    async def test_resolve_shut_list_action_rejects_non_v11(self) -> None:
        """非 v11 协议版本直接拒绝。"""
        bot = MagicMock()
        bot.get_version_info = AsyncMock(
            return_value={"app_name": "LLOneBot", "protocol_version": "v12"}
        )

        action, error = await mute_module._resolve_shut_list_action(bot)

        assert action is None
        assert error


class TestBatchUnmuteAndFormatting:
    """批量解禁与「禁言列表」格式化 / 审计解析。"""

    def test_batch_unmute_calls_set_group_ban_with_zero_duration(self) -> None:
        """解禁必须用 duration=0（用 1 会把成员重新禁言 1 秒）。"""
        bot = MagicMock()
        bot.set_group_ban = AsyncMock()
        members = [MutedMember(user_id=10001, display_name="甲")]

        asyncio.run(mute_module._batch_unmute(bot, group_id=999, members=members))

        bot.set_group_ban.assert_awaited_once_with(
            group_id=999, user_id=10001, duration=0
        )

    def test_batch_unmute_does_not_abort_on_failure(self) -> None:
        """失败必须只记录并继续 —— 不能 return 中断后续成员。"""
        bot = MagicMock()
        calls: list[int] = []

        async def fake_ban(**kwargs: object) -> None:
            user_id = int(str(kwargs["user_id"]))
            calls.append(user_id)
            raise OneBot11ActionFailed

        bot.set_group_ban = AsyncMock(side_effect=fake_ban)
        members = [
            MutedMember(user_id=1, display_name="甲"),
            MutedMember(user_id=2, display_name="乙"),
            MutedMember(user_id=3, display_name="丙"),
        ]

        ok, failed = asyncio.run(
            mute_module._batch_unmute(bot, group_id=999, members=members)
        )

        assert calls == [1, 2, 3], "失败后未继续处理后续成员"
        assert ok == []
        assert [m.user_id for m in failed] == [1, 2, 3]

    def test_batch_unmute_collects_failures(self) -> None:
        """_batch_unmute 返回 (成功, 失败)，顺序执行且失败不重试。"""
        bot = MagicMock()
        calls: list[int] = []

        async def fake_ban(**kwargs: object) -> None:
            user_id = int(str(kwargs["user_id"]))
            calls.append(user_id)
            if user_id == 10002:
                raise OneBot11ActionFailed

        bot.set_group_ban = AsyncMock(side_effect=fake_ban)
        members = [
            MutedMember(user_id=10001, display_name="甲"),
            MutedMember(user_id=10002, display_name="乙"),
            MutedMember(user_id=10003, display_name="丙"),
        ]

        ok, failed = asyncio.run(
            mute_module._batch_unmute(bot, group_id=999, members=members)
        )

        assert calls == [10001, 10002, 10003]
        assert [m.user_id for m in ok] == [10001, 10003]
        assert [m.user_id for m in failed] == [10002]
        assert bot.set_group_ban.await_count == 3

    def test_format_remaining_boundaries(self) -> None:
        """剩余时间格式化的单位切换与边界。"""
        assert mute_module._format_remaining(0) == "0 秒"
        assert mute_module._format_remaining(-5) == "0 秒"
        assert mute_module._format_remaining(45) == "45 秒"
        assert mute_module._format_remaining(90) == "1 分 30 秒"
        assert mute_module._format_remaining(3600) == "1 小时"
        assert mute_module._format_remaining(90000) == "1 天 1 小时"

    def test_parse_mute_audit_summary(self) -> None:
        """从审计 data_summary 里取出 target/duration/reason。"""
        summary = (
            "operator=123, target=10001, action=member_mute, group=999, "
            "duration=600, reason=刷屏"
        )
        parsed = mute_module._parse_mute_audit_summary(summary)

        assert parsed["target"] == "10001"
        assert parsed["duration"] == "600"
        assert parsed["reason"] == "刷屏"

    def test_parse_mute_audit_summary_partial_and_reason_with_commas(self) -> None:
        """无 duration/reason 时缺键；reason 内含逗号不被截断。"""
        parsed = mute_module._parse_mute_audit_summary(
            "operator=1, target=2, action=member_mute, group=3"
        )
        assert parsed.get("target") == "2"
        assert "duration" not in parsed
        assert "reason" not in parsed

        parsed2 = mute_module._parse_mute_audit_summary(
            "operator=1, target=2, action=member_mute, group=3, duration=60, "
            "reason=刷屏, 重复, 广告"
        )
        assert parsed2["reason"] == "刷屏, 重复, 广告"

    def test_parse_mute_audit_summary_empty(self) -> None:
        """空 / None 输入返回空 dict，不抛。"""
        assert mute_module._parse_mute_audit_summary(None) == {}
        assert mute_module._parse_mute_audit_summary("") == {}

    def test_format_mute_list_report_shows_remaining_and_reason(self) -> None:
        """列表行含一对一标识、剩余时间与原因；取不到原因时给占位。"""
        members = [
            MutedMember(user_id=10001, display_name="甲", shut_up_time=1000 + 750),
            MutedMember(user_id=10002, display_name="乙", shut_up_time=None),
        ]
        text = mute_module._format_mute_list_report(
            members=members,
            audit_by_target={10001: {"reason": "刷屏"}},
            now_ts=1000,
        )

        assert "甲(10001)" in text
        assert "12 分 30 秒" in text
        assert "原因: 刷屏" in text
        assert "乙(10002)" in text
        assert "剩余 未知" in text
        assert "未知（非本机器人操作或记录已过保留期）" in text


class TestOneBot11MuteList:
    """「禁言列表」handler。"""

    @pytest.fixture(autouse=True)
    def _mock_check_bot_privilege(self):
        with patch.object(
            mute_module, "check_bot_privilege", new=AsyncMock(return_value=True)
        ):
            yield

    @pytest.fixture(autouse=True)
    def _mock_handle_config_manager(self):
        with patch.object(
            mute_module, "get_handle_config_manager", return_value=_EnabledManager()
        ):
            yield

    @pytest.mark.asyncio
    async def test_mute_list_shows_members_with_remaining(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """列表显示成员一对一信息与**确切**的剩余时间。

        冻结处理器时钟后断言数值：只断言「剩余」二字会让错误的时间计算（例如
        恒显示 0 秒）照样通过。
        """
        now = 1_700_000_000
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            return_value=[{"uin": "10001", "nick": "甲", "shutUpTime": now + 750}]
        )

        with (
            patch.object(mute_module.time, "time", return_value=now),
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        text = finish_text(mock_finish)
        assert "甲(10001)" in text
        assert "剩余 12 分 30 秒" in text

    @pytest.mark.asyncio
    async def test_mute_list_uses_audit_reason(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """能从审计记录取回原因时显示真实原因。"""
        shut_up_time = 2**31 - 1
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            return_value=[{"uin": "10001", "nick": "甲", "shutUpTime": shut_up_time}]
        )
        record = MagicMock()
        record.data_summary = (
            "operator=1, target=10001, action=member_mute, "
            f"group={mock_onebot11_event.group_id}, duration=600, reason=刷屏"
        )
        # 该审计推算的解禁时刻必须与当前禁言一致，否则视为上一轮遗留记录
        record.created_at = datetime.fromtimestamp(shut_up_time - 600, UTC)

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(return_value=[record]),
            ),
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        assert "原因: 刷屏" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_list_ignores_reason_containing_group_prefix(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """Reason 里恰好含 ``group=999…`` 前缀时，仍不得冒充本群记录。

        这道用例专门钉住「解析后按 group 精确比较」这一步：只靠子串匹配会被
        前缀骗过（``group=999999999`` 含有 ``group=999`` 前缀）。
        """
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            return_value=[{"uin": "10001", "nick": "甲"}]
        )

        gid = mock_onebot11_event.group_id
        record = MagicMock()
        record.data_summary = (
            "operator=1, target=10001, action=member_mute, "
            f"group={gid + 1}, duration=600, reason=群里提到 group={gid} 这个号"
        )

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(return_value=[record]),
            ),
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        text = finish_text(mock_finish)
        assert "群里提到" not in text, "别的群的记录被前缀匹配骗过了"

    @pytest.mark.asyncio
    async def test_mute_list_ignores_other_group_audit(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """别的群的审计记录不得被当成本群的（按群号二次过滤）。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            return_value=[{"uin": "10001", "nick": "甲"}]
        )

        record = MagicMock()
        record.data_summary = (
            "operator=1, target=10001, action=member_mute, "
            "group=999999999, duration=600, reason=别的群的原因"
        )

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(return_value=[record]),
            ),
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        assert "别的群的原因" not in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_list_empty(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """没人被禁言时回执说明，且不查审计。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(return_value=[])

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(),
            ) as mock_audits,
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_audits.assert_not_called()
        assert "没有被禁言" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_list_unsupported_protocol(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """协议端不支持时回可读文案。"""
        mock_onebot11_bot.get_version_info = AsyncMock(
            return_value={"app_name": "NapCat.Onebot", "protocol_version": "v11"}
        )

        with patch.object(mute_list_cmd, "finish") as mock_finish:
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        assert "不支持" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_list_survives_audit_query_failure(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """审计查询失败只降级为「未知原因」，不影响列出成员。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            return_value=[{"uin": "10001", "nick": "甲"}]
        )

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(side_effect=DatabaseError("boom")),
            ),
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        text = finish_text(mock_finish)
        assert "甲(10001)" in text
        assert "未知（非本机器人操作或记录已过保留期）" in text


class TestReMutedDuringOperation:
    """#3：操作期间被他人再次禁言的成员，必须在报告里单独标出（不谎报为单纯成功）。"""

    @pytest.fixture(autouse=True)
    def _mock_record_audit(self):
        with patch.object(mute_module, "record_audit_fire_and_forget", new=MagicMock()):
            yield

    @pytest.fixture(autouse=True)
    def _mock_check_bot_privilege(self):
        with patch.object(
            mute_module, "check_bot_privilege", new=AsyncMock(return_value=True)
        ):
            yield

    @pytest.fixture(autouse=True)
    def _mock_handle_config_manager(self):
        with patch.object(
            mute_module, "get_handle_config_manager", return_value=_EnabledManager()
        ):
            yield

    @pytest.mark.asyncio
    async def test_member_re_muted_by_others_is_flagged(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """乙 解禁后又被别人禁言 → 报告里以 ⚠️ 单独列出，不计入普通成功行。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=[
                [
                    {"uin": "10001", "nick": "甲"},
                    {"uin": "10002", "nick": "乙"},
                ],
                # 复查：乙 又被别人禁言了
                [{"uin": "10002", "nick": "乙", "shutUpTime": 2**31 - 1}],
            ]
        )
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(one_click_unmute_cmd, "finish") as mock_finish:
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        text = finish_text(mock_finish)
        assert mock_onebot11_bot.call_api.await_count == 2, "未做解禁后复查"
        assert "⚠️ 乙(10002)" in text, text
        assert "✅ 乙(10002)" not in text, "被再次禁言的人不该只报成功"
        assert "✅ 甲(10001)" in text

    @pytest.mark.asyncio
    async def test_recheck_failure_does_not_break_report(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """复查失败只少一段提示，不能把已完成的解禁变成报错。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=[
                [{"uin": "10001", "nick": "甲"}],
                OneBot11ActionFailed(),
            ]
        )
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(one_click_unmute_cmd, "finish") as mock_finish:
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        text = finish_text(mock_finish)
        assert "✅ 甲(10001)" in text, text
        assert "⚠️" not in text

    @pytest.mark.asyncio
    async def test_audit_carries_outcome_counts(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """#10：汇总审计要带上成功/失败人数，事后可追查影响面。"""
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=[
                [
                    {"uin": "1", "nick": "甲"},
                    {"uin": "2", "nick": "乙"},
                ],
                [],
            ]
        )
        mock_onebot11_bot.set_group_ban = AsyncMock(
            side_effect=[None, OneBot11ActionFailed()]
        )

        with (
            patch.object(
                mute_module, "record_audit_fire_and_forget", new=MagicMock()
            ) as mock_audit,
            patch.object(one_click_unmute_cmd, "finish"),
        ):
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        assert mock_audit.call_count == 1
        audit = mock_audit.call_args.args[2]
        assert audit.action == "one_click_unmute"
        assert audit.outcome, "批量命令的审计缺影响面摘要"
        assert "1" in audit.outcome and "1" in audit.outcome
