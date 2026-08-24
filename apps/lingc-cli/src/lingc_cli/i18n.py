"""gettext-based internationalization for Lingc CLI."""

from __future__ import annotations

from functools import lru_cache
import gettext as gettext_module
import os
from pathlib import Path

DOMAIN = "messages"
DEFAULT_LOCALE = "en"
LOCALES_DIR = Path(__file__).parent / "locales"

_LOCALE_ENV = "LINGC_LOCALE"
_LOCALE_ALIASES = {"zh": "zh_CN"}


def normalize_locale(locale: str | None) -> str:
    """Normalize a locale name for gettext (zh-CN -> zh_CN, strip encoding)."""
    if not locale:
        return DEFAULT_LOCALE
    normalized = locale.strip().replace("-", "_")
    if "." in normalized:
        normalized = normalized.split(".", maxsplit=1)[0]
    return _LOCALE_ALIASES.get(normalized, normalized) or DEFAULT_LOCALE


def _os_locale() -> str:
    """Return the OS-declared locale (LC_ALL > LC_MESSAGES > LANG)."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return normalize_locale(value)
    return DEFAULT_LOCALE


def get_locale() -> str:
    """Resolve the active locale: LINGC_LOCALE override, else OS declaration."""
    return normalize_locale(os.environ.get(_LOCALE_ENV) or _os_locale())


@lru_cache(maxsize=16)
def get_translation(locale: str | None = None) -> gettext_module.NullTranslations:
    """Return a cached gettext translation object (fallback to source strings)."""
    return gettext_module.translation(
        DOMAIN,
        localedir=LOCALES_DIR,
        languages=[normalize_locale(locale)],
        fallback=True,
    )


def gettext(message: str) -> str:
    """Translate a message via the active locale."""
    return get_translation(get_locale()).gettext(message)


_ = gettext

__all__ = [
    "DEFAULT_LOCALE",
    "DOMAIN",
    "LOCALES_DIR",
    "_",
    "get_locale",
    "get_translation",
    "gettext",
    "normalize_locale",
]
