"""gettext-based internationalization helpers."""

from __future__ import annotations

import asyncio
import gettext as gettext_module
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

DOMAIN = "messages"
DEFAULT_LOCALE = "en_US"
LOCALES_DIR = Path(__file__).parent / "locales"


def normalize_locale(locale: str | None) -> str:
    """Normalize user-provided locale names for gettext."""
    if not locale:
        return DEFAULT_LOCALE

    normalized = locale.strip().replace("-", "_")
    if "." in normalized:
        normalized = normalized.split(".", maxsplit=1)[0]
    return normalized or DEFAULT_LOCALE


@lru_cache(maxsize=1)
def _read_configured_locale() -> str:
    """Read and cache the locale from initialized NoneBot config."""
    from nonebot import get_driver

    config = get_driver().config

    for key in ("lingchu_locale", "lc_locale", "locale"):
        value = getattr(config, key, None)
        if isinstance(value, str) and value.strip():
            return normalize_locale(value)

    return DEFAULT_LOCALE


def get_configured_locale() -> str:
    """Read the configured locale from NoneBot config if available."""
    try:
        return _read_configured_locale()
    except (ImportError, ValueError):
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


async def get_translation_async(
    locale: str | None = None,
) -> gettext_module.NullTranslations:
    """Return a cached gettext translation object without blocking the loop."""
    return await asyncio.to_thread(get_translation, locale)


def gettext(message: str, locale: str | None = None) -> str:
    """Translate a singular message."""
    return get_translation(locale or get_configured_locale()).gettext(message)


async def gettext_async(message: str, locale: str | None = None) -> str:
    """Translate a singular message without blocking the event loop."""
    translation = await get_translation_async(locale or get_configured_locale())
    return translation.gettext(message)


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


async def ngettext_async(
    singular: str,
    plural: str,
    n: int,
    locale: str | None = None,
) -> str:
    """Translate a pluralized message without blocking the event loop."""
    translation = await get_translation_async(locale or get_configured_locale())
    return translation.ngettext(singular, plural, n)


async def warm_translation_cache(locales: Iterable[str | None] | None = None) -> None:
    """Load gettext catalogs in worker threads before async handlers need them."""
    if locales is None:
        locales = (get_configured_locale(), DEFAULT_LOCALE)

    normalized = {normalize_locale(locale) for locale in locales}
    await asyncio.gather(
        *(get_translation_async(locale) for locale in normalized),
        return_exceptions=False,
    )


_ = gettext
_async = gettext_async

__all__ = [
    "DEFAULT_LOCALE",
    "DOMAIN",
    "LOCALES_DIR",
    "_",
    "_async",
    "get_configured_locale",
    "get_translation",
    "get_translation_async",
    "gettext",
    "gettext_async",
    "ngettext",
    "ngettext_async",
    "normalize_locale",
    "warm_translation_cache",
]
