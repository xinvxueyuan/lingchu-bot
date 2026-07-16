from unittest.mock import patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.platforms import (
    PlatformAdapterConflictError,
    PlatformAdapterNotLoadedError,
    PlatformAdapterUnknownError,
    PlatformCapability,
    get_platform_profile,
    get_protocol_implementations,
    get_supported_adapter_names,
    get_supported_adapters,
    is_adapter_enabled,
    is_known_adapter,
    iter_platform_profiles,
    parse_configured_adapters,
    resolve_adapter_id,
    resolve_enabled_adapters,
    validate_platform_adapter_selection,
)


def test_default_qq_profile_uses_onebot_v11() -> None:
    profile = get_platform_profile("OneBot V11")

    assert profile is not None
    assert profile.platform_id == "qq"
    assert PlatformCapability.MEMBER_MODERATION in profile.capabilities
    assert get_platform_profile("Milky") is None


def test_qq_profile_supports_application_operation() -> None:
    profile = get_platform_profile("OneBot V11")

    assert profile is not None
    assert PlatformCapability.APPLICATION_OPERATION in profile.capabilities


def test_supported_adapters_are_declared_from_profiles() -> None:
    assert get_supported_adapters() == {"~onebot.v11"}


def test_configured_adapter_selects_known_platform_adapter() -> None:
    assert get_supported_adapters("~onebot.v11") == {"~onebot.v11"}


def test_resolve_adapter_id_normalizes_display_and_canonical_names() -> None:
    assert resolve_adapter_id("OneBot V11") == "~onebot.v11"
    assert resolve_adapter_id("unknown") is None


def test_configured_unknown_adapter_raises() -> None:
    with pytest.raises(PlatformAdapterUnknownError) as exc_info:
        get_supported_adapters("~telegram+~onebot.v11+~discord")

    assert exc_info.value.adapters == frozenset({"~telegram", "~discord"})


def test_deprecated_adapter_id_falls_through_to_unknown_error() -> None:
    """Deprecated adapter ids now raise PlatformAdapterUnknownError."""
    with pytest.raises(PlatformAdapterUnknownError) as exc_info:
        get_supported_adapters("~milky")

    assert exc_info.value.adapters == frozenset({"~milky"})


def test_runtime_same_platform_adapters_are_allowed_when_default_is_loaded() -> None:
    validate_platform_adapter_selection(("Milky", "OneBot V11"), configured=None)


def test_configured_adapter_suppresses_runtime_conflict() -> None:
    validate_platform_adapter_selection(
        ("Milky", "OneBot V11"),
        configured="~onebot.v11",
    )
    assert not is_adapter_enabled("Milky", "~onebot.v11")


def test_default_adapter_must_be_loaded() -> None:
    with pytest.raises(PlatformAdapterNotLoadedError) as exc_info:
        validate_platform_adapter_selection(("Telegram",), configured=None)

    assert exc_info.value.adapter_id == "~onebot.v11"
    assert exc_info.value.registered_adapters == frozenset()


def test_configured_adapter_must_be_loaded() -> None:
    with pytest.raises(PlatformAdapterNotLoadedError) as exc_info:
        validate_platform_adapter_selection((), configured="~onebot.v11")

    assert exc_info.value.adapter_id == "~onebot.v11"
    assert exc_info.value.registered_adapters == frozenset()


def test_configured_adapter_passes_when_loaded_with_extra_adapters() -> None:
    validate_platform_adapter_selection(
        ("OneBot V11", "Telegram"),
        configured="~onebot.v11",
    )


def test_iter_platform_profiles_defaults_to_implemented() -> None:
    assert [profile.platform_id for profile in iter_platform_profiles()] == ["qq"]


def test_is_adapter_enabled_returns_false_for_unknown_adapter() -> None:
    """未知适配器不应被视为已启用。"""
    assert not is_adapter_enabled("NonexistentAdapter")


def test_get_platform_profile_returns_none_for_unknown_adapter() -> None:
    """未知适配器没有对应的平台 profile。"""
    assert get_platform_profile("UnknownProtocol") is None


def test_qq_profile_has_permission_module() -> None:
    """QQ 平台 profile 设置了 permission_module 字段。"""
    profile = get_platform_profile("OneBot V11")

    assert profile is not None
    assert profile.permission_module == "..platforms.qq.permissions"


# ---------------------------------------------------------------------------
# Coverage gap tests
# ---------------------------------------------------------------------------


def test_iter_platform_profiles_returns_all_when_including_unimplemented() -> None:
    """implemented_only=False 时走 else 分支，返回全部 profiles。"""
    all_profiles = iter_platform_profiles(implemented_only=False)
    implemented_profiles = iter_platform_profiles()

    assert len(all_profiles) >= 1
    assert all_profiles == implemented_profiles


def test_parse_configured_adapters_accepts_list_input() -> None:
    """非字符串输入走 tuple(configured) 分支。"""
    result = parse_configured_adapters(["onebot.v11", "~onebot.v11"])

    assert result == ("~onebot.v11", "~onebot.v11")


def test_parse_configured_adapters_skips_empty_segments() -> None:
    """空字符串片段应被跳过（覆盖 continue 分支）。"""
    result = parse_configured_adapters("~onebot.v11++~onebot.v11")

    assert result == ("~onebot.v11", "~onebot.v11")


def test_parse_configured_adapters_prefixes_tilde_when_missing() -> None:
    """无 ~ 前缀的输入会被自动补上。"""
    assert parse_configured_adapters("onebot.v11") == ("~onebot.v11",)


def test_resolve_adapter_id_returns_none_for_empty_or_whitespace() -> None:
    """空字符串或纯空白应返回 None（覆盖 _resolve_known_adapter_id 早返回）。"""
    assert resolve_adapter_id("") is None
    assert resolve_adapter_id("   ") is None


def test_resolve_enabled_adapters_returns_configured_adapter() -> None:
    """resolve_enabled_adapters 直接调用返回配置的 adapter。"""
    assert resolve_enabled_adapters("~onebot.v11") == {"~onebot.v11"}
    assert resolve_enabled_adapters(None) == {"~onebot.v11"}


def test_is_known_adapter_returns_true_for_known_names() -> None:
    """已知适配器名返回 True（覆盖 is_known_adapter 主体）。"""
    assert is_known_adapter("OneBot V11")
    assert is_known_adapter("onebot11")
    assert is_known_adapter("~onebot.v11")


def test_is_known_adapter_returns_false_for_unknown_name() -> None:
    """未知适配器名返回 False。"""
    assert not is_known_adapter("NonexistentAdapter")
    assert not is_known_adapter("~unknown.adapter")


def test_get_supported_adapter_names_returns_sorted_display_names() -> None:
    """get_supported_adapter_names 返回排序后的展示名。"""
    names = get_supported_adapter_names()

    assert isinstance(names, tuple)
    assert names == tuple(sorted(names))
    assert "onebot v11" in names
    assert "onebot11" in names


def test_get_protocol_implementations_returns_all_when_no_filter() -> None:
    """无 filter 时返回所有 protocol 实现（覆盖 adapter_id is None 分支）。"""
    impls = get_protocol_implementations()

    assert len(impls) >= 2
    protocol_ids = {impl.protocol_id for impl in impls}
    assert "default" in protocol_ids
    assert "napcat" in protocol_ids


def test_get_protocol_implementations_filters_by_known_adapter_id() -> None:
    """按已知 adapter_id 过滤 protocol 实现（覆盖过滤分支）。"""
    impls = get_protocol_implementations("~onebot.v11")

    assert all(impl.adapter_id == "~onebot.v11" for impl in impls)
    assert len(impls) >= 1


def test_get_protocol_implementations_returns_empty_for_unknown_adapter_id() -> None:
    """未知 adapter_id 返回空元组。"""
    assert get_protocol_implementations("~unknown.adapter") == ()


def test_platform_adapter_conflict_error_includes_available_adapters_for_known_platform() -> (
    None
):
    """PlatformAdapterConflictError 对已知 platform_id 走 if profile 分支。"""
    error = PlatformAdapterConflictError(
        platform_id="qq",
        adapters=frozenset({"~onebot.v11", "~onebot.v12"}),
        source="test",
    )

    assert error.platform_id == "qq"
    assert error.adapters == frozenset({"~onebot.v11", "~onebot.v12"})
    assert error.source == "test"
    message = str(error)
    assert "~onebot.v11" in message
    assert "LINGCHUAdapter" in message


def test_platform_adapter_conflict_error_falls_back_for_unknown_platform() -> None:
    """PlatformAdapterConflictError 对未知 platform_id 走 else 分支。"""
    error = PlatformAdapterConflictError(
        platform_id="unknown_platform",
        adapters=frozenset({"~adapter.a", "~adapter.b"}),
        source="test",
    )

    assert error.platform_id == "unknown_platform"
    message = str(error)
    assert "~adapter.a" in message
    assert "~adapter.b" in message


def test_platform_adapter_not_loaded_error_with_unknown_adapter_id() -> None:
    """PlatformAdapterNotLoadedError 对未知 adapter_id 走 profile is None 分支。"""
    error = PlatformAdapterNotLoadedError(
        adapter_id="~unknown.adapter",
        registered_adapters=frozenset(),
    )

    assert error.adapter_id == "~unknown.adapter"
    assert error.registered_adapters == frozenset()
    message = str(error)
    assert "~unknown.adapter" in message
    assert "none" in message


def test_profile_enabled_adapter_raises_conflict_when_multiple_adapters_match_profile() -> (
    None
):
    """_profile_enabled_adapter 在多个适配器匹配同一 profile 时抛出 conflict error。"""
    from src.plugins.nonebot_plugin_lingchu_bot.platforms import registry

    qq_profile = registry.PLATFORM_PROFILES[0]
    fake_index = {"~onebot.v12": qq_profile}
    with patch.dict(registry._ADAPTER_PROFILE_INDEX, fake_index, clear=False):
        with pytest.raises(PlatformAdapterConflictError) as exc_info:
            registry._profile_enabled_adapter(
                qq_profile,
                ("~onebot.v11", "~onebot.v12"),
                source="test",
            )

        assert exc_info.value.platform_id == "qq"
        assert exc_info.value.adapters == frozenset({"~onebot.v11", "~onebot.v12"})
