import pytest

from src.plugins.nonebot_plugin_lingchu_bot.i18n import (
    _,
    gettext,
    normalize_locale,
)


@pytest.mark.i18n
def test_gettext_uses_configured_catalog(configured_locale: str) -> None:
    expected = {
        "zh_CN": "全体禁言成功",
        "en_US": "Whole-group mute enabled",
    }
    assert _("全体禁言成功") == expected[configured_locale]


@pytest.mark.i18n
def test_gettext_translates_message(locale: str) -> None:
    expected = {
        "全体禁言成功": {
            "zh_CN": "全体禁言成功",
            "en_US": "Whole-group mute enabled",
        },
        "灵初功能菜单": {
            "zh_CN": "灵初功能菜单",
            "en_US": "Lingchu Menu",
        },
        "管理员操作「默认」": {
            "zh_CN": "管理员操作「默认」",
            "en_US": "Administrator action (default)",
        },
    }
    for message, translations in expected.items():
        assert gettext(message, locale=locale) == translations[locale]


@pytest.mark.i18n
def test_gettext_falls_back_for_unknown_message(locale: str) -> None:
    assert gettext("未翻译文本", locale=locale) == "未翻译文本"


def test_normalize_locale() -> None:
    assert normalize_locale("en-US.UTF-8") == "en_US"
