from src.plugins.nonebot_plugin_lingchu_bot.permissions.platforms import (
    iter_default_identity_groups,
)


def test_qq_default_identity_groups_are_platform_defined() -> None:
    groups = {seed.group_id: seed for seed in iter_default_identity_groups()}

    assert groups["qq.group"].platform_id == "qq"
    assert groups["qq.group.owner"].parent_group_id == "qq.group"
    assert groups["qq.group.admin"].parent_group_id == "qq.group"
    assert groups["qq.group.member"].parent_group_id == "qq.group"
