"""TOML-backed runtime menu configuration."""

# ruff: noqa: TRY003

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final

from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ..database.toml_store import (
    DatabaseError,
    ensure_toml_dict_file_async,
    load_toml_dict_async,
)
from ..handle import menu as menu_module
from ..handle.menu import LocalizedText, MenuFeature, MenuPage
from .schemas import MENU_SCHEMA_BASENAME

MENU_FILENAME: Final = "menu.toml"
MENU_CONFIG_VERSION: Final = 2


class MenuConfigError(RuntimeError):
    """Menu TOML configuration loading failed."""

    def __init__(self, config_file: Path, reason: BaseException | str) -> None:
        self.config_file = config_file
        super().__init__(f"Invalid Lingchu menu config {config_file}: {reason}")


@dataclass(slots=True)
class _MergeContext:
    path: Path
    default_page_by_id: dict[str, MenuPage]
    feature_by_key: dict[str, MenuFeature]
    feature_sections: dict[str, str]
    updates: dict[str, dict[str, LocalizedText]]
    feature_order: list[str]


def get_menu_config_file() -> Path:
    """Return the localstore-backed menu config file path."""
    try:
        return get_plugin_config_file(MENU_FILENAME)
    except ValueError:
        return Path(MENU_FILENAME)


def menu_config_defaults() -> dict[str, Any]:
    """Return TOML-compatible defaults generated from code-owned menu data."""
    return {
        "version": MENU_CONFIG_VERSION,
        "pages": [_serialize_page(page) for page in menu_module._DEFAULT_MENU_PAGES],
    }


async def load_menu_config(
    config_file: str | Path | None = None,
) -> tuple[tuple[MenuPage, ...], tuple[MenuFeature, ...]]:
    """Load menu pages and features from TOML, merged onto code defaults."""
    path = Path(config_file) if config_file is not None else get_menu_config_file()
    try:
        raw_config = await load_toml_dict_async(
            path,
            default=menu_config_defaults(),
            merge_default=False,
        )
    except DatabaseError as exc:
        raise MenuConfigError(path, exc) from exc

    try:
        return _merge_menu_config(raw_config, path)
    except MenuConfigError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise MenuConfigError(path, exc) from exc


async def ensure_menu_config_file_async(
    config_file: str | Path | None = None,
) -> Path:
    """Create the default menu TOML config file on first startup."""
    path = Path(config_file) if config_file is not None else get_menu_config_file()
    try:
        return await ensure_toml_dict_file_async(
            path,
            menu_config_defaults(),
            schema_basename=MENU_SCHEMA_BASENAME,
        )
    except DatabaseError as exc:
        raise MenuConfigError(path, exc) from exc


def _serialize_page(page: MenuPage) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": page.id,
        "title": _serialize_localized_text(page.title),
    }
    if page.command is not None:
        result["command"] = _serialize_localized_text(page.command)
    items = [
        _serialize_feature(feature)
        for feature in menu_module._DEFAULT_MENU_FEATURES
        if feature.section_id == page.id
    ]
    if items:
        result["items"] = items
    if page.children:
        result["children"] = [_serialize_page(child) for child in page.children]
    return result


def _serialize_feature(feature: MenuFeature) -> dict[str, Any]:
    return {
        "command_key": feature.command_key,
        "summary": _serialize_localized_text(feature.summary),
        "usage": _serialize_localized_text(feature.usage),
    }


def _serialize_localized_text(text: LocalizedText) -> dict[str, str]:
    return {"zh_CN": text.zh_cn, "en_US": text.en_us}


def _merge_menu_config(
    raw_config: dict[str, Any],
    path: Path,
) -> tuple[tuple[MenuPage, ...], tuple[MenuFeature, ...]]:
    default_pages = menu_module._DEFAULT_MENU_PAGES
    default_features = menu_module._DEFAULT_MENU_FEATURES
    context = _MergeContext(
        path=path,
        default_page_by_id={page.id: page for page in _flatten_pages(default_pages)},
        feature_by_key={feature.command_key: feature for feature in default_features},
        feature_sections={},
        updates={},
        feature_order=[],
    )

    raw_pages = raw_config.get("pages", menu_config_defaults()["pages"])
    if not isinstance(raw_pages, list):
        raise TypeError("pages must be an array")
    raw_version = raw_config.get("version", MENU_CONFIG_VERSION)
    if raw_version != MENU_CONFIG_VERSION:
        raise ValueError(
            f"unsupported menu config version {raw_version!r}; "
            f"expected {MENU_CONFIG_VERSION}"
        )

    pages = _merge_pages(
        raw_pages,
        default_pages,
        context,
    )
    default_feature_keys = [feature.command_key for feature in default_features]
    ordered_feature_keys = [
        *context.feature_order,
        *(key for key in default_feature_keys if key not in context.feature_order),
    ]
    features = tuple(
        _merge_feature(
            context.feature_by_key[command_key],
            context.updates.get(command_key),
            context.feature_sections,
        )
        for command_key in ordered_feature_keys
    )
    return pages, features


def _merge_pages(
    raw_pages: list[Any],
    default_pages: tuple[MenuPage, ...],
    context: _MergeContext,
) -> tuple[MenuPage, ...]:
    result: list[MenuPage] = []
    seen: set[str] = set()

    for raw_page in raw_pages:
        if not isinstance(raw_page, dict):
            raise TypeError("page entries must be objects")
        page_id = str(raw_page.get("id", "")).strip()
        default_page = context.default_page_by_id.get(page_id)
        if default_page is None:
            logger.warning(
                f"Lingchu menu config {context.path} references unknown page id "
                f"{page_id!r}; skipping it"
            )
            continue
        if page_id in seen:
            continue
        seen.add(page_id)
        result.append(
            _merge_page(
                raw_page,
                default_page,
                context,
            )
        )

    result.extend(
        default_page for default_page in default_pages if default_page.id not in seen
    )
    return tuple(result)


def _merge_page(
    raw_page: dict[str, Any],
    default_page: MenuPage,
    context: _MergeContext,
) -> MenuPage:
    title = _localized_from_raw(raw_page.get("title"), default_page.title)
    raw_items = raw_page.get("items")
    if raw_items is not None:
        _collect_feature_updates(
            raw_items,
            default_page.id,
            context,
        )

    children = default_page.children
    raw_children = raw_page.get("children")
    if raw_children is not None:
        if not isinstance(raw_children, list):
            raise TypeError(f"children for page {default_page.id!r} must be an array")
        children = _merge_pages(
            raw_children,
            default_page.children,
            context,
        )

    return replace(default_page, title=title, children=children)


def _collect_feature_updates(
    raw_items: Any,
    section_id: str,
    context: _MergeContext,
) -> None:
    if not isinstance(raw_items, list):
        raise TypeError(f"items for page {section_id!r} must be an array")
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise TypeError(f"items for page {section_id!r} must be objects")
        command_key = str(raw_item.get("command_key", "")).strip()
        feature = context.feature_by_key.get(command_key)
        if feature is None:
            raise MenuConfigError(
                context.path,
                f"unknown command_key {command_key!r} in {context.path}",
            )
        context.updates[command_key] = {
            "summary": _localized_from_raw(raw_item.get("summary"), feature.summary),
            "usage": _localized_from_raw(raw_item.get("usage"), feature.usage),
        }
        context.feature_sections[command_key] = section_id
        if command_key not in context.feature_order:
            context.feature_order.append(command_key)


def _merge_feature(
    feature: MenuFeature,
    update: dict[str, LocalizedText] | None,
    feature_sections: dict[str, str],
) -> MenuFeature:
    section_id = feature_sections.get(feature.command_key, feature.section_id)
    if update is None:
        return replace(feature, section_id=section_id)
    return replace(
        feature,
        section_id=section_id,
        summary=update["summary"],
        usage=update["usage"],
    )


def _localized_from_raw(raw: Any, default: LocalizedText) -> LocalizedText:
    if raw is None:
        return default
    if not isinstance(raw, dict):
        raise TypeError("localized text must be an object")
    zh_cn = raw.get("zh_CN", raw.get("zh", default.zh_cn))
    en_us = raw.get("en_US", raw.get("en", default.en_us))
    return LocalizedText(str(zh_cn), str(en_us))


def _flatten_pages(pages: tuple[MenuPage, ...]) -> tuple[MenuPage, ...]:
    result: list[MenuPage] = []
    for page in pages:
        result.append(page)
        result.extend(_flatten_pages(page.children))
    return tuple(result)
