from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from arclet.alconna import Alconna
from nonebot import logger
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_localstore import get_plugin_config_file

from ..database.json5_store import ensure_json5_dict_file_sync, load_json5_dict_sync
from ..i18n import _async as _
from ..i18n import get_configured_locale, gettext, normalize_locale
from ..platforms import resolve_enabled_adapters
from .qq.group.command_triggers import COMMAND_TRIGGERS

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

MENU_FILENAME: Final = "menu.json5"
_MENU = COMMAND_TRIGGERS["menu"]

menu_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_MENU.primary),
    aliases=_MENU.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_ADAPTER_MODULES: dict[str, tuple[str, ...]] = {
    "~onebot.v11": (".qq.onebot.v11.default.menu",),
    "~milky": (".qq.milky.v1_2.default.menu",),
}
_loaded_handlers: dict[str, tuple[Callable[[], Any], ...]] = {}


def default_menu_store() -> dict[str, Any]:
    return {
        "version": 1,
        "sections": [
            {
                "id": "member-management",
                "title": {"zh_CN": "成员管理", "en_US": "Member Management"},
                "items": [
                    _item(
                        "kick_member",
                        zh_summary="踢出群成员",
                        en_summary="Kick a group member",
                        zh_usage="@用户 [是否拒绝再次申请]",
                        en_usage="@user [reject add request]",
                    ),
                    _item(
                        "set_member_card",
                        zh_summary="设置群名片",
                        en_summary="Set a member card",
                        zh_usage="@用户 <名片>",
                        en_usage="@user <card>",
                    ),
                    _item(
                        "set_member_title",
                        zh_summary="设置群头衔",
                        en_summary="Set a member special title",
                        zh_usage="@用户 <头衔>",
                        en_usage="@user <title>",
                    ),
                    _item(
                        "set_member_admin",
                        zh_summary="设置群管理员",
                        en_summary="Promote a member to admin",
                        zh_usage="@用户 [true/false]",
                        en_usage="@user [true/false]",
                    ),
                    _item(
                        "unset_member_admin",
                        zh_summary="取消群管理员",
                        en_summary="Revoke member admin",
                        zh_usage="@用户",
                        en_usage="@user",
                    ),
                ],
            },
            {
                "id": "speech-management",
                "title": {"zh_CN": "发言管理", "en_US": "Speech Management"},
                "items": [
                    _item(
                        "member_mute",
                        zh_summary="禁言群成员",
                        en_summary="Mute a member",
                        zh_usage="@用户 [时长秒数] [原因]",
                        en_usage="@user [duration seconds] [reason]",
                    ),
                    _item(
                        "member_unmute",
                        zh_summary="解除成员禁言",
                        en_summary="Unmute a member",
                        zh_usage="@用户 [原因]",
                        en_usage="@user [reason]",
                    ),
                    _item(
                        "whole_mute",
                        zh_summary="开启全体禁言",
                        en_summary="Enable whole-group mute",
                    ),
                    _item(
                        "whole_unmute",
                        zh_summary="关闭全体禁言",
                        en_summary="Disable whole-group mute",
                    ),
                ],
            },
            {
                "id": "group-profile",
                "title": {"zh_CN": "群资料", "en_US": "Group Profile"},
                "items": [
                    _item(
                        "set_group_name",
                        zh_summary="设置群名称",
                        en_summary="Set group name",
                        zh_usage="<新群名称>",
                        en_usage="<new group name>",
                    ),
                    _item(
                        "set_group_avatar",
                        zh_summary="设置群头像",
                        en_summary="Set group avatar",
                        zh_usage="<图片>",
                        en_usage="<image>",
                    ),
                ],
            },
            {
                "id": "announcement",
                "title": {"zh_CN": "群公告", "en_US": "Announcement"},
                "items": [
                    _item(
                        "send_announcement",
                        zh_summary="发送群公告",
                        en_summary="Send group announcement",
                        zh_usage="<内容> [图片]",
                        en_usage="<content> [image]",
                    )
                ],
            },
            {
                "id": "group-operation",
                "title": {"zh_CN": "群操作", "en_US": "Group Operation"},
                "items": [
                    _item(
                        "leave_group",
                        zh_summary="退出当前群",
                        en_summary="Leave current group",
                    )
                ],
            },
        ],
    }


def _item(
    command_key: str,
    *,
    zh_summary: str,
    en_summary: str,
    zh_usage: str = "",
    en_usage: str = "",
) -> dict[str, Any]:
    return {
        "command_key": command_key,
        "summary": {"zh_CN": zh_summary, "en_US": en_summary},
        "usage": {"zh_CN": zh_usage, "en_US": en_usage},
    }


def get_menu_store_file() -> Path:
    try:
        return get_plugin_config_file(MENU_FILENAME)
    except ValueError:
        return Path(MENU_FILENAME)


def ensure_menu_store(config_file: str | Path | None = None) -> Path:
    path = Path(config_file) if config_file is not None else get_menu_store_file()
    return ensure_json5_dict_file_sync(path, default_menu_store())


def load_menu_store(config_file: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_file) if config_file is not None else ensure_menu_store()
    ensure_menu_store(path)
    return load_json5_dict_sync(path, default=default_menu_store(), merge_default=True)


def render_menu(
    locale: str | None = None,
    config_file: str | Path | None = None,
) -> str:
    selected_locale = normalize_locale(locale or get_configured_locale())
    store = load_menu_store(config_file)
    lines = [gettext("灵初功能菜单", selected_locale)]

    for section in _iter_sections(store.get("sections")):
        section_lines = _render_section(section, selected_locale)
        if section_lines:
            lines.extend(("", *section_lines))

    return "\n".join(lines)


def _iter_sections(raw_sections: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(raw_sections, list):
        return ()
    return (section for section in raw_sections if isinstance(section, dict))


def _render_section(section: dict[str, Any], locale: str) -> list[str]:
    title = _localized(section.get("title"), locale)
    lines = [f"【{title}】"]

    for item in _iter_items(section.get("items")):
        rendered = _render_item(item, locale)
        if rendered:
            lines.append(rendered)

    if len(lines) == 1:
        return []
    return lines


def _iter_items(raw_items: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return ()
    return (item for item in raw_items if isinstance(item, dict))


def _render_item(item: dict[str, Any], locale: str) -> str:
    command_key = item.get("command_key")
    if not isinstance(command_key, str) or command_key not in COMMAND_TRIGGERS:
        logger.debug(f"Lingchu 菜单跳过未知命令: {command_key!r}")
        return ""

    trigger = COMMAND_TRIGGERS[command_key]
    command = trigger.primary_for(locale)
    usage = _localized(item.get("usage"), locale)
    summary = _localized(item.get("summary"), locale)
    command_text = f"{command} {usage}".strip()
    return f"- {summary}: {command_text}"


def _localized(value: Any, locale: str) -> str:
    if isinstance(value, dict):
        if locale.lower().startswith("en"):
            result = value.get("en_US") or value.get("en") or value.get("zh_CN")
        else:
            result = value.get("zh_CN") or value.get("zh") or value.get("en_US")
        return str(result or "")
    if value is None:
        return ""
    return str(value)


def _load_adapter_handlers(adapter_id: str) -> tuple[Callable[[], Any], ...]:
    if adapter_id in _loaded_handlers:
        return _loaded_handlers[adapter_id]

    handlers: list[Callable[[], Any]] = []
    for module_name in _ADAPTER_MODULES.get(adapter_id, ()):
        mod = import_module(module_name, __package__)
        if hasattr(mod, "import_handle"):
            handlers.append(mod.import_handle)
    _loaded_handlers[adapter_id] = tuple(handlers)
    return _loaded_handlers[adapter_id]


async def import_handle() -> Any:
    logger.debug(await _("导入menu处理器..."))
    ensure_menu_store()
    for adapter_id in sorted(resolve_enabled_adapters()):
        handlers = _load_adapter_handlers(adapter_id)
        if not handlers:
            logger.debug(
                (await _("Lingchu 未为适配器 {adapter_id} 声明 menu 处理器")).format(
                    adapter_id=adapter_id
                )
            )
            continue
        logger.debug(
            (await _("Lingchu 为适配器 {adapter_id} 导入 menu 处理器")).format(
                adapter_id=adapter_id
            )
        )
        for handler in handlers:
            await handler()
