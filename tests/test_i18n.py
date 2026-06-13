from src.plugins.nonebot_plugin_lingchu_bot.i18n import (
    _,
    gettext,
    normalize_locale,
)


def test_gettext_uses_default_chinese_catalog() -> None:
    assert _("全体禁言成功") == "全体禁言成功"


def test_gettext_can_use_english_catalog() -> None:
    assert gettext("全体禁言成功", locale="en-US") == "Whole-group mute enabled"
    assert gettext("灵初功能菜单", locale="en-US") == "Lingchu Menu"
    assert gettext("管理员操作「默认」", locale="en-US") == (
        "Administrator action (default)"
    )


def test_gettext_falls_back_for_unknown_message() -> None:
    assert gettext("未翻译文本", locale="en_US") == "未翻译文本"


def test_normalize_locale() -> None:
    assert normalize_locale("en-US.UTF-8") == "en_US"
