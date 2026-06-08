import pytest

from src.plugins.nonebot_plugin_lingchu_bot.platforms import (
    PlatformAdapterConflictError,
    PlatformAdapterNotLoadedError,
    PlatformAdapterUnknownError,
    PlatformCapability,
    get_platform_profile,
    get_supported_adapters,
    is_adapter_enabled,
    iter_platform_profiles,
    resolve_adapter_id,
    validate_platform_adapter_selection,
)


def test_default_qq_profile_uses_onebot_v11() -> None:
    profile = get_platform_profile("OneBot V11")

    assert profile is not None
    assert profile.platform_id == "qq"
    assert PlatformCapability.MEMBER_MODERATION in profile.capabilities
    assert get_platform_profile("Milky") is None


def test_supported_adapters_are_declared_from_profiles() -> None:
    assert get_supported_adapters() == {"~onebot.v11"}


def test_configured_adapter_selects_known_platform_adapter() -> None:
    assert get_supported_adapters("~onebot.v11") == {"~onebot.v11"}


def test_resolve_adapter_id_normalizes_display_and_canonical_names() -> None:
    assert resolve_adapter_id("OneBot V11") == "~onebot.v11"
    assert resolve_adapter_id("~milky") == "~milky"
    assert resolve_adapter_id("unknown") is None


def test_configured_unknown_adapter_raises() -> None:
    with pytest.raises(PlatformAdapterUnknownError) as exc_info:
        get_supported_adapters("~telegram+~onebot.v11+~discord")

    assert exc_info.value.adapters == frozenset({"~telegram", "~discord"})


def test_configured_milky_selects_milky_profile() -> None:
    profile = get_platform_profile("Milky", "~milky")

    assert get_supported_adapters("~milky") == {"~milky"}
    assert profile is not None
    assert profile.platform_id == "qq"


def test_configured_same_platform_adapters_raise() -> None:
    with pytest.raises(PlatformAdapterConflictError) as exc_info:
        get_supported_adapters("~milky+~onebot.v11")

    assert exc_info.value.platform_id == "qq"
    assert exc_info.value.source == "configuration"


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
        validate_platform_adapter_selection(("Milky",), configured=None)

    assert exc_info.value.adapter_id == "~onebot.v11"
    assert exc_info.value.registered_adapters == frozenset({"~milky"})


def test_configured_adapter_must_be_loaded() -> None:
    with pytest.raises(PlatformAdapterNotLoadedError) as exc_info:
        validate_platform_adapter_selection(("OneBot V11",), configured="~milky")

    assert exc_info.value.adapter_id == "~milky"
    assert exc_info.value.registered_adapters == frozenset({"~onebot.v11"})


def test_configured_adapter_passes_when_loaded_with_extra_adapters() -> None:
    validate_platform_adapter_selection(
        ("Milky", "OneBot V11"),
        configured="~milky",
    )


def test_unknown_registered_adapter_does_not_affect_selection() -> None:
    validate_platform_adapter_selection(
        ("Milky", "OneBot V11", "Telegram"),
        configured="~milky",
    )


def test_iter_platform_profiles_defaults_to_implemented() -> None:
    assert [profile.platform_id for profile in iter_platform_profiles()] == ["qq"]


def test_is_adapter_enabled_returns_false_for_unknown_adapter() -> None:
    """未知适配器不应被视为已启用。"""
    assert not is_adapter_enabled("NonexistentAdapter")


def test_get_platform_profile_returns_none_for_unknown_adapter() -> None:
    """未知适配器没有对应的平台 profile。"""
    assert get_platform_profile("UnknownProtocol") is None
