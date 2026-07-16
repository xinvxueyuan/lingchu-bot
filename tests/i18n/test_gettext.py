import pytest

from src.plugins.nonebot_plugin_lingchu_bot import i18n as i18n_module
from src.plugins.nonebot_plugin_lingchu_bot.i18n import (
    DEFAULT_LOCALE,
    _,
    get_configured_locale,
    gettext,
    gettext_async,
    ngettext,
    ngettext_async,
    normalize_locale,
    warm_translation_cache,
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


def test_normalize_locale_returns_default_for_none_and_empty() -> None:
    assert normalize_locale(None) == DEFAULT_LOCALE
    assert normalize_locale("") == DEFAULT_LOCALE


def test_normalize_locale_returns_default_for_whitespace_only() -> None:
    assert normalize_locale("   ") == DEFAULT_LOCALE


@pytest.mark.asyncio
@pytest.mark.i18n
async def test_gettext_async_translates_message(locale: str) -> None:
    translated = await gettext_async("全体禁言成功", locale=locale)
    expected = {
        "zh_CN": "全体禁言成功",
        "en_US": "Whole-group mute enabled",
    }
    assert translated == expected[locale]


@pytest.mark.i18n
def test_ngettext_translates_singular_and_plural(locale: str) -> None:
    singular = ngettext("item", "items", 1, locale=locale)
    plural = ngettext("item", "items", 2, locale=locale)

    assert singular == "item"
    assert plural == "items"


@pytest.mark.asyncio
@pytest.mark.i18n
async def test_ngettext_async_translates_singular_and_plural(locale: str) -> None:
    singular = await ngettext_async("item", "items", 1, locale=locale)
    plural = await ngettext_async("item", "items", 2, locale=locale)

    assert singular == "item"
    assert plural == "items"


def test_read_configured_locale_returns_default_when_attribute_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover the ``return DEFAULT_LOCALE`` branch in ``_read_configured_locale``."""
    from types import SimpleNamespace

    i18n_module._read_configured_locale.cache_clear()
    fake_driver = SimpleNamespace(config=SimpleNamespace())
    monkeypatch.setattr("nonebot.get_driver", lambda: fake_driver)

    try:
        assert i18n_module._read_configured_locale() == DEFAULT_LOCALE
    finally:
        i18n_module._read_configured_locale.cache_clear()


def test_get_configured_locale_returns_default_on_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_import_error() -> str:
        raise ImportError

    monkeypatch.setattr(i18n_module, "_read_configured_locale", _raise_import_error)

    assert get_configured_locale() == DEFAULT_LOCALE


def test_get_configured_locale_returns_default_on_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_value_error() -> str:
        raise ValueError

    monkeypatch.setattr(i18n_module, "_read_configured_locale", _raise_value_error)

    assert get_configured_locale() == DEFAULT_LOCALE


@pytest.mark.asyncio
@pytest.mark.i18n
async def test_warm_translation_cache_uses_default_locales_when_omitted(
    configured_locale: str,
) -> None:
    _ = configured_locale
    await warm_translation_cache()


@pytest.mark.asyncio
@pytest.mark.i18n
async def test_warm_translation_cache_accepts_explicit_locales(
    locale: str,
) -> None:
    await warm_translation_cache([locale])
