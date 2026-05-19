"""gettext-based internationalization helpers."""

from __future__ import annotations

import gettext as gettext_module
from functools import lru_cache
from pathlib import Path

DOMAIN = "messages"
DEFAULT_LOCALE = "zh_CN"
LOCALES_DIR = Path(__file__).parent / "locales"


def normalize_locale(locale: str | None) -> str:
    """Normalize user-provided locale names for gettext."""
    if not locale:
        return DEFAULT_LOCALE

    normalized = locale.strip().replace("-", "_")
    if "." in normalized:
        normalized = normalized.split(".", maxsplit=1)[0]
    return normalized or DEFAULT_LOCALE


def get_configured_locale() -> str:
    """Read the configured locale from NoneBot config if available."""
    try:
        from nonebot import get_driver

        config = get_driver().config
    except (ImportError, ValueError):
        return DEFAULT_LOCALE

    for key in ("lingchu_locale", "lc_locale", "locale"):
        value = getattr(config, key, None)
        if isinstance(value, str) and value.strip():
            return normalize_locale(value)

    return DEFAULT_LOCALE


@lru_cache(maxsize=16)
def get_translation(locale: str | None = None) -> gettext_module.NullTranslations:
    """Return a cached gettext translation object."""
    return gettext_module.translation(
        DOMAIN,
        localedir=LOCALES_DIR,
        languages=[normalize_locale(locale)],
        fallback=True,
    )


def gettext(message: str, locale: str | None = None) -> str:
    """Translate a singular message."""
    return get_translation(locale or get_configured_locale()).gettext(message)


def ngettext(
    singular: str,
    plural: str,
    n: int,
    locale: str | None = None,
) -> str:
    """Translate a pluralized message."""
    return get_translation(locale or get_configured_locale()).ngettext(
        singular,
        plural,
        n,
    )


_ = gettext

__all__ = [
    "DEFAULT_LOCALE",
    "DOMAIN",
    "LOCALES_DIR",
    "_",
    "get_configured_locale",
    "get_translation",
    "gettext",
    "ngettext",
    "normalize_locale",
]
