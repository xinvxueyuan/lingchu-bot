import pytest

from src.plugins.nonebot_plugin_lingchu_bot.platforms import (
    PlatformAdapterConflictError,
    PlatformCapability,
    get_platform_profile,
    get_supported_adapters,
    is_adapter_enabled,
    iter_platform_profiles,
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
    assert get_supported_adapters("~telegram+~onebot.v11+~discord") == {"~onebot.v11"}


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


def test_runtime_same_platform_adapters_raise_without_config() -> None:
    with pytest.raises(PlatformAdapterConflictError) as exc_info:
        validate_platform_adapter_selection(("Milky", "OneBot V11"), configured=None)

    assert exc_info.value.platform_id == "qq"
    assert exc_info.value.source == "runtime"


def test_configured_adapter_suppresses_runtime_conflict() -> None:
    validate_platform_adapter_selection(
        ("Milky", "OneBot V11"),
        configured="~onebot.v11",
    )
    assert not is_adapter_enabled("Milky", "~onebot.v11")


def test_iter_platform_profiles_defaults_to_implemented() -> None:
    assert [profile.platform_id for profile in iter_platform_profiles()] == ["qq"]
