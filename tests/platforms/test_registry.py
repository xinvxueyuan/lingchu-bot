from src.plugins.nonebot_plugin_lingchu_bot.platforms import (
    PlatformCapability,
    get_platform_profile,
    get_supported_adapters,
    iter_platform_profiles,
)


def test_qq_profile_groups_existing_adapters() -> None:
    profile = get_platform_profile("Milky")

    assert profile is not None
    assert profile.platform_id == "qq"
    assert PlatformCapability.MEMBER_MODERATION in profile.capabilities


def test_supported_adapters_are_declared_from_profiles() -> None:
    assert get_supported_adapters() == {"~milky", "~onebot.v11"}


def test_iter_platform_profiles_defaults_to_implemented() -> None:
    assert [profile.platform_id for profile in iter_platform_profiles()] == ["qq"]
