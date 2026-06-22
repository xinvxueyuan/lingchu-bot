"""
测试机器人状态控制 - 静默模式与handle门禁

覆盖范围：
- 全局状态标志读写（bot_state 模块）
- 闭嘴/说话/开机/关机四个命令处理器
- _state_wrapper 门禁阻断与放行行为
- _silent_call 静默抑制与 finish 恢复行为
- 集成场景：门禁关闭时全体禁言被阻断、静默模式下全体禁言抑制 finish
"""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.exception import FinishedException

from src.plugins.nonebot_plugin_lingchu_bot.core import bot_state as bot_state_module
from src.plugins.nonebot_plugin_lingchu_bot.core.bot_state import (
    _reset_state_for_testing,
    get_platform_handle_active,
    get_platform_silent_mode,
    is_handle_active,
    is_silent_mode,
    set_global_handle_active,
    set_global_silent_mode,
    set_platform_handle_active,
    set_platform_silent_mode,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    bot_state as bot_state_handlers,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    mute as mute_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.bot_state import (
    bot_boot_cmd,
    bot_shutdown_cmd,
    bot_silence_cmd,
    bot_speak_cmd,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.common import (
    _silent_call,
    _state_wrapper,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.mute import (
    whole_mute_cmd,
)
from tests.handle.commands.conftest import finish_text

# 直接引用模块内的处理器函数，避免过长的 import 行
onebot11_bot_boot = bot_state_handlers.onebot11_bot_boot
onebot11_bot_shutdown = bot_state_handlers.onebot11_bot_shutdown
onebot11_bot_silence = bot_state_handlers.onebot11_bot_silence
onebot11_bot_speak = bot_state_handlers.onebot11_bot_speak
onebot11_whole_mute = mute_module.onebot11_whole_mute


@pytest.fixture(autouse=True)
def _reset_bot_state() -> Any:
    """每个测试前后重置机器人状态标志为默认值。"""
    _reset_state_for_testing()
    yield
    _reset_state_for_testing()


@pytest.fixture(autouse=True)
def _mock_fire_and_forget() -> Any:
    """避免审计记录和状态持久化触发后台任务。"""
    captured: list[tuple[Any, str]] = []

    def _spy(coro: Any, *, name: str = "fire_and_forget") -> Any:
        captured.append((coro, name))
        return MagicMock()

    with (
        patch.object(mute_module, "record_audit_fire_and_forget", new=AsyncMock()),
        patch.object(bot_state_module, "fire_and_forget", side_effect=_spy),
    ):
        yield
    for coro, _name in captured:
        coro.close()


# ================= 状态标志测试 =================


class TestBotStateFlags:
    """机器人状态标志读写测试。"""

    def test_default_handle_active(self) -> None:
        """测试默认状态下 handle 门禁为开启。"""
        assert is_handle_active("qq") is True

    def test_default_silent_mode(self) -> None:
        """测试默认状态下静默模式为关闭。"""
        assert is_silent_mode("qq") is False

    def test_set_handle_active_false(self) -> None:
        """测试关闭 handle 门禁。"""
        set_global_handle_active(active=False)
        assert is_handle_active("qq") is False

    def test_set_silent_mode_true(self) -> None:
        """测试开启静默模式。"""
        set_global_silent_mode(silent=True)
        assert is_silent_mode("qq") is True

    def test_toggle_handle_active(self) -> None:
        """测试 handle 门禁开关切换。"""
        set_global_handle_active(active=False)
        assert is_handle_active("qq") is False
        set_global_handle_active(active=True)
        assert is_handle_active("qq") is True

    def test_toggle_silent_mode(self) -> None:
        """测试静默模式开关切换。"""
        set_global_silent_mode(silent=True)
        assert is_silent_mode("qq") is True
        set_global_silent_mode(silent=False)
        assert is_silent_mode("qq") is False


class TestTwoTierResolution:
    """两层状态模型解析逻辑测试。"""

    def test_global_gate_off_overrides_platform_on(self) -> None:
        """全局门禁关闭时，即使平台门禁开启也返回 False。"""
        set_global_handle_active(active=False)
        set_platform_handle_active("qq", active=True)
        assert is_handle_active("qq") is False

    def test_global_gate_on_respects_platform_off(self) -> None:
        """全局门禁开启时，平台门禁关闭则返回 False。"""
        set_global_handle_active(active=True)
        set_platform_handle_active("qq", active=False)
        assert is_handle_active("qq") is False

    def test_global_silent_on_overrides_platform_off(self) -> None:
        """全局静默开启时，即使平台静默关闭也返回 True。"""
        set_global_silent_mode(silent=True)
        set_platform_silent_mode("qq", silent=False)
        assert is_silent_mode("qq") is True

    def test_global_silent_off_respects_platform_on(self) -> None:
        """全局静默关闭时，平台静默开启则返回 True。"""
        set_global_silent_mode(silent=False)
        set_platform_silent_mode("qq", silent=True)
        assert is_silent_mode("qq") is True

    def test_unknown_platform_defaults_to_permissive(self) -> None:
        """未知平台默认为放行状态（handle_active=True, silent_mode=False）。"""
        assert is_handle_active("unknown") is True
        assert is_silent_mode("unknown") is False

    def test_platform_handle_active_default_true(self) -> None:
        """平台门禁默认为 True。"""
        assert get_platform_handle_active("new_platform") is True

    def test_platform_silent_mode_default_false(self) -> None:
        """平台静默模式默认为 False。"""
        assert get_platform_silent_mode("new_platform") is False


class TestPlatformState:
    """平台级状态管理测试。"""

    def test_set_platform_handle_active(self) -> None:
        """测试设置平台级门禁。"""
        set_platform_handle_active("qq", active=False)
        assert get_platform_handle_active("qq") is False
        assert is_handle_active("qq") is False

    def test_set_platform_silent_mode(self) -> None:
        """测试设置平台级静默模式。"""
        set_platform_silent_mode("qq", silent=True)
        assert get_platform_silent_mode("qq") is True
        assert is_silent_mode("qq") is True

    def test_platform_state_independent(self) -> None:
        """测试不同平台状态互不影响。"""
        set_platform_handle_active("qq", active=False)
        set_platform_handle_active("discord", active=True)
        assert is_handle_active("qq") is False
        assert is_handle_active("discord") is True

    def test_global_and_platform_both_off(self) -> None:
        """测试全局和平台都关闭时结果为 False。"""
        set_global_handle_active(active=False)
        set_platform_handle_active("qq", active=False)
        assert is_handle_active("qq") is False


# ================= 闭嘴命令处理器测试 =================


class TestBotSilenceHandler:
    """闭嘴命令处理器测试。"""

    @pytest.mark.asyncio
    async def test_bot_silence_sets_silent_mode(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试闭嘴命令开启静默模式并返回提示消息。"""
        with patch.object(bot_silence_cmd, "finish") as mock_finish:
            await onebot11_bot_silence(bot=mock_onebot11_bot, event=mock_onebot11_event)

        assert is_silent_mode("qq") is True
        assert finish_text(mock_finish) == "已进入静默模式"


# ================= 说话命令处理器测试 =================


class TestBotSpeakHandler:
    """说话命令处理器测试。"""

    @pytest.mark.asyncio
    async def test_bot_speak_clears_silent_mode(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试说话命令关闭静默模式并返回提示消息。"""
        set_global_silent_mode(silent=True)

        with patch.object(bot_speak_cmd, "finish") as mock_finish:
            await onebot11_bot_speak(bot=mock_onebot11_bot, event=mock_onebot11_event)

        assert is_silent_mode("qq") is False
        assert finish_text(mock_finish) == "已退出静默模式"


# ================= 开机命令处理器测试 =================


class TestBotBootHandler:
    """开机命令处理器测试。"""

    @pytest.mark.asyncio
    async def test_bot_boot_sets_handle_active(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试开机命令开启 handle 门禁并返回提示消息。"""
        set_global_handle_active(active=False)

        with patch.object(bot_boot_cmd, "finish") as mock_finish:
            await onebot11_bot_boot(bot=mock_onebot11_bot, event=mock_onebot11_event)

        assert is_handle_active("qq") is True
        assert finish_text(mock_finish) == "已开机"


# ================= 关机命令处理器测试 =================


class TestBotShutdownHandler:
    """关机命令处理器测试。"""

    @pytest.mark.asyncio
    async def test_bot_shutdown_clears_handle_active(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试关机命令关闭 handle 门禁并返回提示消息。"""
        with patch.object(bot_shutdown_cmd, "finish") as mock_finish:
            await onebot11_bot_shutdown(
                bot=mock_onebot11_bot, event=mock_onebot11_event
            )

        assert is_handle_active("qq") is False
        assert finish_text(mock_finish) == "已关机"


# ================= 门禁阻断测试 =================


class TestGateBlocking:
    """handle 门禁阻断行为测试。"""

    @pytest.mark.asyncio
    async def test_gate_off_blocks_handler(self) -> None:
        """测试门禁关闭时 _state_wrapper 阻断处理器调用。"""
        called = False

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal called
            called = True
            return "result"

        mock_cmd: Any = MagicMock()
        wrapped = _state_wrapper(
            mock_cmd, fake_handler, platform_id="qq", check_gate=True
        )

        set_global_handle_active(active=False)
        result = await wrapped()

        assert result is None
        assert called is False

    @pytest.mark.asyncio
    async def test_gate_on_allows_handler(self) -> None:
        """测试门禁开启时 _state_wrapper 放行处理器调用。"""
        called = False

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal called
            called = True
            return "result"

        mock_cmd: Any = MagicMock()
        wrapped = _state_wrapper(
            mock_cmd, fake_handler, platform_id="qq", check_gate=True
        )

        assert is_handle_active("qq") is True
        result = await wrapped()

        assert result == "result"
        assert called is True

    @pytest.mark.asyncio
    async def test_bypass_gate_allows_handler_when_off(self) -> None:
        """测试 check_gate=False 时即使门禁关闭也放行。"""
        called = False

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal called
            called = True
            return "result"

        mock_cmd: Any = MagicMock()
        wrapped = _state_wrapper(
            mock_cmd, fake_handler, platform_id="qq", check_gate=False
        )

        set_global_handle_active(active=False)
        result = await wrapped()

        assert result == "result"
        assert called is True

    @pytest.mark.asyncio
    async def test_gate_takes_precedence_over_silent(self) -> None:
        """测试门禁关闭且静默模式开启时，门禁检查优先阻断。"""
        called = False

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal called
            called = True
            return "result"

        mock_cmd: Any = MagicMock()
        wrapped = _state_wrapper(
            mock_cmd,
            fake_handler,
            platform_id="qq",
            check_gate=True,
            check_silent=True,
        )

        set_global_handle_active(active=False)
        set_global_silent_mode(silent=True)
        result = await wrapped()

        assert result is None
        assert called is False

    @pytest.mark.asyncio
    async def test_gate_off_blocks_whole_mute(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试门禁关闭时全体禁言处理器被阻断且不调用 API。"""
        mock_onebot11_bot.set_group_whole_ban = AsyncMock()
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "admin"}
        )

        wrapped = _state_wrapper(
            whole_mute_cmd, onebot11_whole_mute, platform_id="qq", check_gate=True
        )

        set_global_handle_active(active=False)
        result = await wrapped(bot=mock_onebot11_bot, event=mock_onebot11_event)

        assert result is None
        mock_onebot11_bot.set_group_whole_ban.assert_not_called()

    @pytest.mark.asyncio
    async def test_boot_handler_works_when_gate_off(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试开机命令在门禁关闭时仍可执行（直接调用处理器）。"""
        set_global_handle_active(active=False)

        with patch.object(bot_boot_cmd, "finish") as mock_finish:
            await onebot11_bot_boot(bot=mock_onebot11_bot, event=mock_onebot11_event)

        assert is_handle_active("qq") is True
        assert finish_text(mock_finish) == "已开机"


# ================= 静默抑制测试 =================


class _FakeCommand:
    """模拟匹配器命令类，用于 _state_wrapper 单元测试。"""

    @classmethod
    async def finish(cls, _message: Any = None, **_kwargs: Any) -> Any:
        """模拟 finish 方法。"""
        return "original"


class TestSilentSuppression:
    """静默模式消息抑制行为测试。"""

    @pytest.mark.asyncio
    async def test_silent_mode_suppresses_finish(self) -> None:
        """测试静默模式下 _state_wrapper 抑制 finish 消息。"""

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            await _FakeCommand.finish("消息")
            return "result"

        wrapped = _state_wrapper(
            cast("Any", _FakeCommand), fake_handler, platform_id="qq", check_silent=True
        )

        set_global_silent_mode(silent=True)
        with pytest.raises(FinishedException):
            await wrapped()

    @pytest.mark.asyncio
    async def test_silent_mode_calls_handler(self) -> None:
        """测试静默模式下处理器函数仍被执行。"""
        handler_called = False

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal handler_called
            handler_called = True
            await _FakeCommand.finish("消息")
            return "result"

        wrapped = _state_wrapper(
            cast("Any", _FakeCommand), fake_handler, platform_id="qq", check_silent=True
        )

        set_global_silent_mode(silent=True)
        with pytest.raises(FinishedException):
            await wrapped()

        assert handler_called is True

    @pytest.mark.asyncio
    async def test_bypass_silent_allows_finish_when_silent(self) -> None:
        """测试 check_silent=False 时即使静默模式开启也正常调用。"""
        finish_called = False

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal finish_called
            await _FakeCommand.finish("消息")
            finish_called = True
            return "result"

        wrapped = _state_wrapper(
            cast("Any", _FakeCommand),
            fake_handler,
            platform_id="qq",
            check_silent=False,
        )

        set_global_silent_mode(silent=True)
        result = await wrapped()

        assert result == "result"
        assert finish_called is True

    @pytest.mark.asyncio
    async def test_silent_mode_suppresses_whole_mute_finish(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试静默模式下全体禁言仍执行 API 但抑制 finish 消息。"""
        mock_onebot11_bot.set_group_whole_ban = AsyncMock()
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "admin"}
        )

        wrapped = _state_wrapper(
            whole_mute_cmd, onebot11_whole_mute, platform_id="qq", check_silent=True
        )

        set_global_silent_mode(silent=True)
        with (
            patch.object(whole_mute_cmd, "finish") as mock_finish,
            pytest.raises(FinishedException),
        ):
            await wrapped(bot=mock_onebot11_bot, event=mock_onebot11_event)

        mock_onebot11_bot.set_group_whole_ban.assert_called_once()
        mock_finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_speak_handler_responds_when_silent(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试说话命令在静默模式下仍正常响应（直接调用处理器）。"""
        set_global_silent_mode(silent=True)

        with patch.object(bot_speak_cmd, "finish") as mock_finish:
            await onebot11_bot_speak(bot=mock_onebot11_bot, event=mock_onebot11_event)

        assert is_silent_mode("qq") is False
        assert finish_text(mock_finish) == "已退出静默模式"


# ================= _silent_call 恢复测试 =================


class TestSilentCallRestore:
    """_silent_call 恢复 finish 方法测试。"""

    @pytest.mark.asyncio
    async def test_restores_finish_after_handler(self) -> None:
        """测试 _silent_call 在处理器完成后恢复原始 finish。"""
        original = _FakeCommand.__dict__["finish"]

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            await _FakeCommand.finish("消息")
            return "result"

        with pytest.raises(FinishedException):
            await _silent_call(cast("Any", _FakeCommand), fake_handler)

        assert _FakeCommand.__dict__["finish"] is original

    @pytest.mark.asyncio
    async def test_restores_finish_on_exception(self) -> None:
        """测试 _silent_call 在处理器抛出异常时仍恢复原始 finish。"""
        original = _FakeCommand.__dict__["finish"]

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("error")

        with pytest.raises(RuntimeError, match="error"):
            await _silent_call(cast("Any", _FakeCommand), fake_handler)

        assert _FakeCommand.__dict__["finish"] is original

    @pytest.mark.asyncio
    async def test_deletes_shadow_finish_when_inherited(self) -> None:
        """测试 finish 为继承方法时 _silent_call 删除影子属性。"""

        class Child(_FakeCommand):
            pass

        assert "finish" not in Child.__dict__

        async def fake_handler(*_args: Any, **_kwargs: Any) -> Any:
            await Child.finish("消息")
            return "result"

        with pytest.raises(FinishedException):
            await _silent_call(cast("Any", Child), fake_handler)

        assert "finish" not in Child.__dict__
