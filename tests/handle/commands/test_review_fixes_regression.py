"""审查修复的回归测试（对应四个实测确认的缺陷）。

这些用例的共同点：**不复用被测函数内部会用的 mock**，直接钉住真实契约
（真实列名、真实异常层次、真实截断行为），避免「mock 掉了出问题的那一层」。
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from nonebot.adapters.onebot.v11.exception import (
    ActionFailed as OneBot11ActionFailed,
    NetworkError as OneBot11NetworkError,
)
from nonebot.exception import ApiNotAvailable
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    QQOneBotV11NoneBotAuditRecord as AuditModel,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    mute as mute_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.llbot.mute_list import (
    MutedMember,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.mute import (
    mute_list_cmd,
    one_click_unmute_cmd,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import message_store as repo


class _EnabledManager:
    async def get_config(self, command_key: str) -> HandleConfig:
        return HandleConfig(enabled=True, defaults={}, policies={})


#: LLBot 的版本信息（生产实测的 app_name + v11 协议版本）
LLBOT_VERSION_INFO = {"app_name": "LLOneBot", "protocol_version": "v11"}


def finish_text(mock_finish: MagicMock) -> str:
    if mock_finish.call_args:
        if "message" in mock_finish.call_args.kwargs:
            return str(mock_finish.call_args.kwargs["message"])
        if mock_finish.call_args.args:
            return str(mock_finish.call_args.args[0])
    return ""


def _make_exc(exc: type[BaseException]) -> BaseException:
    """构造异常实例（ApiNotAvailable 需要 adapter_name 参数）。"""
    if exc is ApiNotAvailable:
        return ApiNotAvailable("~onebot.v11")
    return exc()


# --------------------------------------------------------------------------
# 缺陷 1：审计查询用了不存在的列名（api_name），真实 ORM 路径必抛 ValueError
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_query_filters_only_real_columns(mock_session: Mock) -> None:
    """回归：``list_recent_command_audits`` 的过滤键必须都是模型的真实列。

    传未知列时 ``list_items`` 会抛 ``ValueError``（**不是** ``DatabaseError``），
    而调用方只捕获 ``DatabaseError`` —— 结果是整条命令异常、零回执。
    这条用例不看具体值，只钉「键名合法性」，所以将来改列名也会被拦住。
    """
    captured: dict[str, object] = {}

    async def fake_list_items(*args: object, **_kwargs: object) -> list[object]:
        captured["model"] = args[1]
        captured["filters"] = args[2]
        return []

    with patch.object(repo, "list_items", new=fake_list_items):
        await repo.list_recent_command_audits(mock_session, action="member_mute")

    filters = captured["filters"]
    assert isinstance(filters, dict)
    real_columns = {c.name for c in AuditModel.__table__.columns}
    unknown = sorted(set(filters) - real_columns)
    assert not unknown, (
        f"过滤键含不存在的列: {unknown}（真实列: {sorted(real_columns)}）"
    )

    # 值本身也要对上：命令审计存在 event_type 列里
    assert filters["event_type"] == "command:member_mute"


@pytest.mark.asyncio
async def test_audit_query_does_not_use_api_name_key(mock_session: Mock) -> None:
    """回归：明确禁止 ``api_name`` 这个键（模型上没有该列）。"""
    captured: dict[str, object] = {}

    async def fake_list_items(*args: object, **_kwargs: object) -> list[object]:
        captured["filters"] = args[2]
        return []

    with patch.object(repo, "list_items", new=fake_list_items):
        await repo.list_recent_command_audits(mock_session, action="member_mute")

    filters = captured["filters"]
    assert isinstance(filters, dict)
    assert "api_name" not in filters


# --------------------------------------------------------------------------
# 缺陷 2：报告截断把失败行静默吞掉
# --------------------------------------------------------------------------


def _members(prefix: str, count: int, start: int) -> list[MutedMember]:
    return [
        MutedMember(user_id=start + i, display_name=f"{prefix}{i}")
        for i in range(count)
    ]


class TestUnmuteReportTruncation:
    """失败行绝不能被截断（失败是可操作信息）。"""

    def test_failures_survive_when_successes_exceed_limit(self) -> None:
        """回归：成功 30 人 + 失败 2 人时，两条失败都必须出现。

        （修复前：成功行先拼、占满 30 行上限，失败行被整个截掉。）
        """
        succeeded = _members("OK", 30, 1000)
        failed = [
            MutedMember(user_id=9000, display_name="FAILX"),
            MutedMember(user_id=9001, display_name="FAILY"),
        ]

        text = mute_module._format_unmute_report(succeeded=succeeded, failed=failed)

        assert "FAILX" in text
        assert "FAILY" in text
        assert "❌" in text

    def test_failures_survive_at_various_success_counts(self) -> None:
        """成功人数跨过上限的各个位置，失败行都不消失。"""
        failed = [MutedMember(user_id=9000, display_name="FAILX")]
        for n_ok in (0, 1, 28, 29, 30, 31, 60):
            succeeded = _members("OK", n_ok, 1000)
            text = mute_module._format_unmute_report(succeeded=succeeded, failed=failed)
            assert "FAILX" in text, f"成功 {n_ok} 人时失败行消失"

    def test_truncation_only_drops_successes_and_says_so(self) -> None:
        """被截掉的只是成功行，且尾注说明是「成功者未列出」。"""
        text = mute_module._format_unmute_report(
            succeeded=_members("OK", 50, 1000),
            failed=[MutedMember(user_id=9000, display_name="FAILX")],
        )
        assert "未列出" in text
        assert "成功" in text  # 尾注需点明省略的是成功者，不是「有人被忽略」

    def test_short_report_has_no_truncation_note(self) -> None:
        """未超限时不得出现截断尾注。"""
        text = mute_module._format_unmute_report(
            succeeded=_members("OK", 3, 1000),
            failed=[MutedMember(user_id=9000, display_name="FAILX")],
        )
        assert "未列出" not in text
        assert "FAILX" in text


# --------------------------------------------------------------------------
# 缺陷 3：ApiNotAvailable 逃逸，中断整批且无回执
# --------------------------------------------------------------------------


class TestApiNotAvailableHandling:
    """连接不可用（ApiNotAvailable）不属于 ActionFailed/NetworkError。"""

    def test_hierarchy_assumption(self) -> None:
        """钉住假设：ApiNotAvailable 确实不是上述两者的子类。

        如果哪天 nonebot 改了继承关系，这条会失败，提醒我们简化捕获元组。
        """
        assert not issubclass(ApiNotAvailable, OneBot11ActionFailed)
        assert not issubclass(ApiNotAvailable, OneBot11NetworkError)

    def test_batch_unmute_does_not_escape_on_api_not_available(self) -> None:
        """回归：连接不可用时不能让异常逃逸，需按失败记录并继续。"""
        bot = MagicMock()
        calls: list[int] = []

        async def fake_ban(**kwargs: object) -> None:
            calls.append(int(kwargs["user_id"]))  # type: ignore[arg-type]
            raise ApiNotAvailable("~onebot.v11")

        bot.set_group_ban = AsyncMock(side_effect=fake_ban)
        members = _members("M", 3, 1)

        succeeded, failed = asyncio.run(
            mute_module._batch_unmute(bot, group_id=999, members=members)
        )

        assert calls == [1, 2, 3], "ApiNotAvailable 逃逸导致后续成员未被处理"
        assert succeeded == []
        assert [m.user_id for m in failed] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_one_click_unmute_reports_connection_failure(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """连接不可用时给出如实回执，而不是零输出。"""
        mock_onebot11_bot.get_version_info = AsyncMock(
            return_value={"app_name": "LLOneBot", "protocol_version": "v11"}
        )
        mock_onebot11_bot.call_api = AsyncMock(
            return_value={"retcode": 0, "data": [{"uin": "1", "nick": "甲"}]}
        )
        mock_onebot11_bot.set_group_ban = AsyncMock(
            side_effect=ApiNotAvailable("~onebot.v11")
        )

        with (
            patch.object(mute_module, "record_audit_fire_and_forget", new=MagicMock()),
            patch.object(
                mute_module, "check_bot_privilege", new=AsyncMock(return_value=True)
            ),
            patch.object(
                mute_module,
                "get_handle_config_manager",
                return_value=_EnabledManager(),
            ),
            patch.object(one_click_unmute_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_one_click_unmute(
                bot=mock_onebot11_bot, event=mock_onebot11_event, session=mock_session
            )

        text = finish_text(mock_finish)
        assert text, "命令无回执（异常逃逸）"
        assert "❌" in text
        assert "失败 1 人" in text


# --------------------------------------------------------------------------
# 缺陷 4：get_version_info 未包 try，失败时异常冒泡
# --------------------------------------------------------------------------


class TestVersionQueryFailure:
    """版本查询失败需降级为可读文案。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exc",
        [OneBot11ActionFailed, OneBot11NetworkError, ApiNotAvailable],
    )
    async def test_resolve_returns_error_text_on_version_failure(
        self, exc: type[BaseException]
    ) -> None:
        bot = MagicMock()
        bot.get_version_info = AsyncMock(side_effect=_make_exc(exc))

        action, error = await mute_module._resolve_shut_list_action(bot)

        assert action is None
        assert error, f"{exc.__name__} 时未返回可读文案"

    @pytest.mark.asyncio
    async def test_mute_list_responds_when_version_query_fails(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """回归：版本查询失败时 mute-list 有回执，不是零输出。"""
        mock_onebot11_bot.get_version_info = AsyncMock(
            side_effect=OneBot11ActionFailed()
        )

        with (
            patch.object(
                mute_module, "check_bot_privilege", new=AsyncMock(return_value=True)
            ),
            patch.object(
                mute_module,
                "get_handle_config_manager",
                return_value=_EnabledManager(),
            ),
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot, event=mock_onebot11_event, session=mock_session
            )

        assert finish_text(mock_finish), "命令无回执（异常逃逸）"


# --------------------------------------------------------------------------
# bot 审查第二轮：审计时窗、群号下沉过滤、默认原因、原因内 key= 文本、i18n
# --------------------------------------------------------------------------


class TestAuditOnlyMatchesCurrentMute:
    """#5：上一轮的审计不得被当作当前禁言的原因。"""

    def test_matching_window_is_accepted(self) -> None:
        audit = {"duration": "600"}
        # 下达时刻 + 时长 == 当前禁言结束时刻
        assert mute_module._audit_matches_current_mute(
            audit, created_at_ts=1000.0, shut_up_time=1600
        )

    def test_stale_audit_is_rejected(self) -> None:
        """成员被解除后又被别人重新禁言：旧审计的解禁时刻对不上。"""
        audit = {"duration": "600"}
        # 旧审计结束于 1600，但当前禁言结束于 1600 + 3600（重新禁言）
        assert not mute_module._audit_matches_current_mute(
            audit, created_at_ts=1000.0, shut_up_time=5200
        )

    def test_tolerance_boundary(self) -> None:
        """容差边界：恰好等于容差算匹配，超出 1 秒即不匹配。"""
        tol = mute_module.MUTE_AUDIT_END_TOLERANCE_SECONDS
        audit = {"duration": "600"}
        assert mute_module._audit_matches_current_mute(
            audit, created_at_ts=1000.0, shut_up_time=1600 + tol
        )
        assert not mute_module._audit_matches_current_mute(
            audit, created_at_ts=1000.0, shut_up_time=1600 + tol + 1
        )

    @pytest.mark.parametrize(
        ("audit", "created_at_ts", "shut_up_time"),
        [
            ({}, 1000.0, 1600),  # 缺 duration
            ({"duration": "不是数字"}, 1000.0, 1600),  # duration 非法
            ({"duration": "600"}, None, 1600),  # 缺 created_at
            ({"duration": "600"}, 1000.0, None),  # 缺 shut_up_time
        ],
    )
    def test_unverifiable_is_rejected(
        self,
        audit: dict[str, str],
        created_at_ts: float | None,
        shut_up_time: int | None,
    ) -> None:
        """无法确认时一律不挂原因（宁缺勿猜）。"""
        assert not mute_module._audit_matches_current_mute(
            audit, created_at_ts=created_at_ts, shut_up_time=shut_up_time
        )

    @pytest.mark.asyncio
    async def test_handler_shows_unknown_for_stale_audit(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        """端到端：只有旧审计时列表显示「未知」，不显示旧原因。"""
        shut_up = 2**31 - 1
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            return_value=[{"uin": "10001", "nick": "甲", "shutUpTime": shut_up}]
        )

        record = MagicMock()
        record.data_summary = (
            "operator=1, target=10001, action=member_mute, "
            f"group={mock_onebot11_event.group_id}, duration=600, reason=很久以前的原因"
        )
        # 旧审计：结束时刻比当前禁言早很多
        record.created_at = datetime.fromtimestamp(shut_up - 600 - 7200, UTC)

        with (
            patch.object(
                mute_module, "check_bot_privilege", new=AsyncMock(return_value=True)
            ),
            patch.object(
                mute_module, "get_handle_config_manager", return_value=_EnabledManager()
            ),
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(return_value=[record]),
            ),
            patch.object(mute_list_cmd, "finish") as mock_finish,
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot, event=mock_onebot11_event, session=mock_session
            )

        text = finish_text(mock_finish)
        assert "很久以前的原因" not in text
        assert "未知" in text


class TestAuditQueryScopedToGroup:
    """#6：群号过滤必须下沉到查询，否则旧记录被挤出 LIMIT 窗口。"""

    @pytest.mark.asyncio
    async def test_group_id_is_passed_to_repository(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        shut_up = 2**31 - 1
        mock_onebot11_bot.get_version_info = AsyncMock(return_value=LLBOT_VERSION_INFO)
        mock_onebot11_bot.call_api = AsyncMock(
            return_value=[{"uin": "10001", "nick": "甲", "shutUpTime": shut_up}]
        )

        with (
            patch.object(
                mute_module, "check_bot_privilege", new=AsyncMock(return_value=True)
            ),
            patch.object(
                mute_module, "get_handle_config_manager", return_value=_EnabledManager()
            ),
            patch.object(
                mute_module.message_repository,
                "list_recent_command_audits",
                new=AsyncMock(return_value=[]),
            ) as mock_audits,
            patch.object(mute_list_cmd, "finish"),
        ):
            await mute_module.onebot11_mute_list(
                bot=mock_onebot11_bot, event=mock_onebot11_event, session=mock_session
            )

        assert mock_audits.await_args is not None
        assert mock_audits.await_args.kwargs.get("group_id") == (
            mock_onebot11_event.group_id
        ), "群号未下沉到查询 —— 旧记录会被后来的其他群记录挤出窗口"


class TestParseSummaryKeepsReasonText:
    """#8：原因里出现形如 ``key=`` 的文本时不得截断、不得凭空多出字段。"""

    def test_key_like_text_inside_reason_is_kept(self) -> None:
        parsed = mute_module._parse_mute_audit_summary(
            "operator=1, target=2, action=member_mute, group=3, duration=60, "
            "reason=他说 target=1 别刷了"
        )
        assert parsed["reason"] == "他说 target=1 别刷了"
        assert parsed["target"] == "2"  # 真实 target 未被原因里的假键覆盖

    def test_fake_duration_inside_reason_does_not_appear(self) -> None:
        parsed = mute_module._parse_mute_audit_summary(
            "operator=1, target=2, action=member_mute, group=3, duration=60, "
            "reason=刷了 duration=很久"
        )
        assert parsed["reason"] == "刷了 duration=很久"
        assert parsed["duration"] == "60"  # 不是「很久」

    def test_field_like_text_in_reason_does_not_create_bogus_field(self) -> None:
        """原因里的 ``duration=`` 不得凭空造出一个 duration 字段。

        这条专门钉住「reason 之后不再解析字段」：若只靠 setdefault 兜底，真实字段
        缺失时假字段就会冒出来（上面的用例因存在真实 duration 而看不出问题）。
        """
        parsed = mute_module._parse_mute_audit_summary(
            "operator=1, target=2, action=member_mute, group=3, "
            "reason=当时写的是 duration=很久"
        )
        assert "duration" not in parsed, f"凭空多出字段: {parsed}"
        assert parsed["reason"] == "当时写的是 duration=很久"

    def test_whitespace_separated_key_inside_reason_is_kept(self) -> None:
        parsed = mute_module._parse_mute_audit_summary(
            "operator=1, target=2, action=member_mute, group=3, duration=60, "
            "reason=提到 group=4 这个群"
        )
        assert parsed["reason"] == "提到 group=4 这个群"
        assert parsed["group"] == "3"


class TestDefaultReasonIsRecorded:
    """#7：未显式给原因时，审计要记下回执里实际展示的默认原因。"""

    @pytest.mark.asyncio
    async def test_default_reason_goes_into_audit(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.mute import (
            member_mute_cmd,
            onebot11_mute,
        )

        mock_onebot11_bot.set_group_ban = AsyncMock()
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "admin"}
        )

        with (
            patch.object(
                mute_module, "check_target_privilege", new=AsyncMock(return_value=True)
            ),
            patch.object(
                mute_module, "get_handle_config_manager", return_value=_EnabledManager()
            ),
            patch.object(
                mute_module, "record_audit_fire_and_forget", new=MagicMock()
            ) as mock_audit,
            patch.object(member_mute_cmd, "finish") as mock_finish,
        ):
            await onebot11_mute(
                user=987654321,
                duration=300,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
                reason=None,
            )

        assert mock_audit.call_count == 1
        audit = mock_audit.call_args.args[2]
        assert audit.reason, "默认原因未记入审计 —— 列表会显示「未知」"
        # 回执里展示的原因应与审计记录一致
        assert str(audit.reason) in finish_text(mock_finish)


class TestReportLabelsGoThroughI18n:
    """#11：报告正文的标签必须走 i18n，不能硬编码中文。"""

    def test_unmute_report_uses_translator(self) -> None:
        def fake_gettext(msg: str) -> str:
            return f"EN<{msg}>"

        with patch.object(mute_module, "gettext", new=fake_gettext):
            text = mute_module._format_unmute_report(
                succeeded=_members("OK", 40, 1000),
                failed=[MutedMember(user_id=9000, display_name="FAILX")],
            )

        assert "EN<" in text, "报告尾注未走 i18n"
        assert "FAILX" in text

    def test_mute_list_report_uses_translator(self) -> None:
        def fake_gettext(msg: str) -> str:
            return f"EN<{msg}>"

        with patch.object(mute_module, "gettext", new=fake_gettext):
            text = mute_module._format_mute_list_report(
                members=[
                    MutedMember(user_id=10001, display_name="甲", shut_up_time=None)
                ],
                audit_by_target={},
                now_ts=1000,
            )

        assert "EN<" in text, "列表正文未走 i18n"

    def test_mute_list_line_template_is_translated(self) -> None:
        """列表行模板（含「剩余/原因」的那行）必须作为一个 msgid 走 i18n。

        只断言输出里出现 ``EN<`` 是不够的：其它标签（未知/单位）被翻译也会让它成立，
        而行模板本身仍可能是硬编码中文。
        """
        called: list[str] = []

        def fake_gettext(msg: str) -> str:
            called.append(msg)
            return msg

        with patch.object(mute_module, "gettext", new=fake_gettext):
            mute_module._format_mute_list_report(
                members=[MutedMember(user_id=1, display_name="甲", shut_up_time=None)],
                audit_by_target={},
                now_ts=1000,
            )

        assert any("剩余" in m and "原因" in m for m in called), (
            f"行模板未走 i18n；实际翻译的 msgid: {called}"
        )

    def test_remaining_units_use_translator(self) -> None:
        with patch.object(mute_module, "gettext", new=lambda m: f"EN<{m}>"):
            assert "EN<秒>" in mute_module._format_remaining(45)
