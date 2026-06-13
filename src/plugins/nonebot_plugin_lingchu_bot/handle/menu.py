from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, Final

from arclet.alconna import Alconna
from nonebot import logger
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from packaging.version import InvalidVersion, Version, parse

from ..i18n import _async as _
from ..i18n import get_configured_locale, gettext, normalize_locale
from ..platforms import PlatformCapability, resolve_enabled_adapters
from .qq.group.command_triggers import COMMAND_TRIGGERS

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_MENU = COMMAND_TRIGGERS["menu"]
QQ_PLATFORM_ID: Final = "qq"
ONEBOT_V11_ADAPTER_ID: Final = "~onebot.v11"
MILKY_ADAPTER_ID: Final = "~milky"
LLONEBOT_IMPL: Final = "LLOneBot"
NAPCAT_IMPL: Final = "NapCat.Onebot"
LLBOT_IMPL: Final = "LLBot"

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


@dataclass(frozen=True, slots=True)
class LocalizedText:
    zh_cn: str
    en_us: str


@dataclass(frozen=True, slots=True)
class MenuAvailability:
    platform_id: str
    adapter_id: str
    implementation_name: str | None = None
    minimum_version: str | None = None
    protocol_version: str | None = None
    usage_override: LocalizedText | None = None


@dataclass(frozen=True, slots=True)
class MenuFeature:
    id: str
    command_key: str
    section_id: str
    summary: LocalizedText
    usage: LocalizedText
    platform_capability: PlatformCapability
    availability: tuple[MenuAvailability, ...]


@dataclass(frozen=True, slots=True)
class MenuSection:
    id: str
    title: LocalizedText


@dataclass(frozen=True, slots=True)
class MenuPage:
    id: str
    title: LocalizedText
    children: tuple["MenuPage", ...] = ()
    command: LocalizedText | None = None


@dataclass(frozen=True, slots=True)
class MenuRuntimeContext:
    platform_id: str
    adapter_id: str
    implementation_name: str | None = None
    implementation_version: str | None = None
    protocol_version: str | None = None
    platform_capabilities: frozenset[PlatformCapability] = frozenset()


QQ_CAPABILITIES: Final[frozenset[PlatformCapability]] = frozenset(
    {
        PlatformCapability.GROUP_MANAGEMENT,
        PlatformCapability.MEMBER_MODERATION,
        PlatformCapability.MEMBER_PROFILE,
        PlatformCapability.GROUP_PROFILE,
        PlatformCapability.ANNOUNCEMENT,
    }
)

MENU_PAGES: Final[tuple[MenuPage, ...]] = (
    MenuPage(
        "member-management",
        LocalizedText("成员管理", "Member Management"),
        command=LocalizedText("成员管理", "member-management"),
    ),
    MenuPage(
        "speech-management",
        LocalizedText("发言管理", "Speech Management"),
        command=LocalizedText("发言管理", "speech-management"),
    ),
    MenuPage(
        "group-chat-management",
        LocalizedText("群聊管理", "Group Chat Management"),
        children=(
            MenuPage("group-profile", LocalizedText("群资料", "Group Profile")),
            MenuPage("announcement", LocalizedText("群公告", "Announcement")),
            MenuPage("group-operation", LocalizedText("群操作", "Group Operation")),
        ),
        command=LocalizedText("群聊管理", "group-chat-management"),
    ),
)
MENU_SECTIONS: Final[tuple[MenuSection, ...]] = tuple(
    MenuSection(page.id, page.title) for page in MENU_PAGES
)
MENU_PAGE_COMMANDS: Final[tuple[MenuPage, ...]] = tuple(
    page for page in MENU_PAGES if page.command is not None
)


def _flatten_pages(pages: Iterable[MenuPage]) -> tuple[MenuPage, ...]:
    result: list[MenuPage] = []
    for page in pages:
        result.append(page)
        result.extend(_flatten_pages(page.children))
    return tuple(result)


_MENU_PAGE_BY_ID: Final[dict[str, MenuPage]] = {
    page.id: page for page in _flatten_pages(MENU_PAGES)
}


def _menu_page_command(page: MenuPage) -> str:
    command = page.command
    if command is None:
        return ""
    locale = normalize_locale(get_configured_locale())
    return command.en_us if locale.lower().startswith("en") else command.zh_cn


menu_page_cmds: Final[dict[str, type[AlconnaMatcher]]] = {
    page.id: on_alconna(
        command=Alconna(_menu_page_command(page)),
        priority=5,
        block=True,
        use_cmd_sep=True,
        use_cmd_start=True,
    )
    for page in MENU_PAGE_COMMANDS
}

_QQ_BOTH: Final[tuple[MenuAvailability, ...]] = (
    MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),
    MenuAvailability(QQ_PLATFORM_ID, MILKY_ADAPTER_ID),
)
_ONEBOT_NAPCAT: Final[tuple[MenuAvailability, ...]] = (
    MenuAvailability(
        QQ_PLATFORM_ID,
        ONEBOT_V11_ADAPTER_ID,
        implementation_name=NAPCAT_IMPL,
        minimum_version="4.18.0",
        protocol_version="v11",
    ),
)
_ONEBOT_ANNOUNCEMENT: Final[tuple[MenuAvailability, ...]] = (
    MenuAvailability(
        QQ_PLATFORM_ID,
        ONEBOT_V11_ADAPTER_ID,
        implementation_name=LLONEBOT_IMPL,
        minimum_version="7.12.0",
        protocol_version="v11",
    ),
    *_ONEBOT_NAPCAT,
)
_MILKY_LLBOT_ANNOUNCEMENT: Final[tuple[MenuAvailability, ...]] = (
    MenuAvailability(
        QQ_PLATFORM_ID,
        MILKY_ADAPTER_ID,
        implementation_name=LLBOT_IMPL,
        usage_override=LocalizedText("<内容>", "<content>"),
    ),
)

MENU_FEATURES: Final[tuple[MenuFeature, ...]] = (
    MenuFeature(
        "kick-member",
        "kick_member",
        "member-management",
        LocalizedText("踢出群成员", "Kick a group member"),
        LocalizedText("@用户", "@user"),
        PlatformCapability.MEMBER_MODERATION,
        _QQ_BOTH,
    ),
    MenuFeature(
        "set-member-card",
        "set_member_card",
        "member-management",
        LocalizedText("设置群名片", "Set a member card"),
        LocalizedText("@用户 <名片>", "@user <card>"),
        PlatformCapability.MEMBER_PROFILE,
        _QQ_BOTH,
    ),
    MenuFeature(
        "set-member-title",
        "set_member_title",
        "member-management",
        LocalizedText("设置群头衔", "Set a member special title"),
        LocalizedText("@用户 <头衔>", "@user <title>"),
        PlatformCapability.MEMBER_PROFILE,
        _QQ_BOTH,
    ),
    MenuFeature(
        "set-member-admin",
        "set_member_admin",
        "member-management",
        LocalizedText("设置群管理员", "Promote a member to admin"),
        LocalizedText("@用户 [true/false]", "@user [true/false]"),
        PlatformCapability.MEMBER_MODERATION,
        _QQ_BOTH,
    ),
    MenuFeature(
        "unset-member-admin",
        "unset_member_admin",
        "member-management",
        LocalizedText("取消群管理员", "Revoke member admin"),
        LocalizedText("@用户", "@user"),
        PlatformCapability.MEMBER_MODERATION,
        _QQ_BOTH,
    ),
    MenuFeature(
        "member-mute",
        "member_mute",
        "speech-management",
        LocalizedText("禁言群成员", "Mute a member"),
        LocalizedText("@用户 [时长秒数] [原因]", "@user [duration seconds] [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        _QQ_BOTH,
    ),
    MenuFeature(
        "member-unmute",
        "member_unmute",
        "speech-management",
        LocalizedText("解除成员禁言", "Unmute a member"),
        LocalizedText("@用户 [原因]", "@user [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        _QQ_BOTH,
    ),
    MenuFeature(
        "whole-mute",
        "whole_mute",
        "speech-management",
        LocalizedText("开启全体禁言", "Enable whole-group mute"),
        LocalizedText("", ""),
        PlatformCapability.MEMBER_MODERATION,
        _QQ_BOTH,
    ),
    MenuFeature(
        "whole-unmute",
        "whole_unmute",
        "speech-management",
        LocalizedText("关闭全体禁言", "Disable whole-group mute"),
        LocalizedText("", ""),
        PlatformCapability.MEMBER_MODERATION,
        _QQ_BOTH,
    ),
    MenuFeature(
        "set-group-name",
        "set_group_name",
        "group-profile",
        LocalizedText("设置群名称", "Set group name"),
        LocalizedText("<新群名称>", "<new group name>"),
        PlatformCapability.GROUP_PROFILE,
        _QQ_BOTH,
    ),
    MenuFeature(
        "set-group-avatar",
        "set_group_avatar",
        "group-profile",
        LocalizedText("设置群头像", "Set group avatar"),
        LocalizedText("<图片>", "<image>"),
        PlatformCapability.GROUP_PROFILE,
        (
            *_ONEBOT_NAPCAT,
            MenuAvailability(QQ_PLATFORM_ID, MILKY_ADAPTER_ID),
        ),
    ),
    MenuFeature(
        "send-announcement",
        "send_announcement",
        "announcement",
        LocalizedText("发送群公告", "Send group announcement"),
        LocalizedText("<内容> [图片]", "<content> [image]"),
        PlatformCapability.ANNOUNCEMENT,
        (*_ONEBOT_ANNOUNCEMENT, *_MILKY_LLBOT_ANNOUNCEMENT),
    ),
    MenuFeature(
        "leave-group",
        "leave_group",
        "group-operation",
        LocalizedText("退出当前群", "Leave current group"),
        LocalizedText("", ""),
        PlatformCapability.GROUP_MANAGEMENT,
        _QQ_BOTH,
    ),
)


def render_menu(
    locale: str | None = None,
    context: MenuRuntimeContext | None = None,
) -> str:
    return render_menu_index(context or default_menu_context(), locale)


def render_menu_index(
    context: MenuRuntimeContext,
    locale: str | None = None,
) -> str:
    selected_locale = normalize_locale(locale or get_configured_locale())
    lines = [gettext("灵初功能菜单", selected_locale)]

    for page in MENU_PAGE_COMMANDS:
        if not _page_has_visible_content(page, context):
            continue
        title = _localized(page.title, selected_locale)
        command = _localized(page.command, selected_locale)
        lines.append(_render_menu_index_entry(title, command))

    return "\n".join(lines)


def _render_menu_index_entry(title: str, command: str) -> str:
    if title.strip() == command.strip():
        return f"- {title}"
    return f"- {title}: {command}"


def render_menu_for_context(
    context: MenuRuntimeContext,
    locale: str | None = None,
) -> str:
    return render_menu_index(context, locale)


def render_menu_page(
    page_id: str,
    context: MenuRuntimeContext,
    locale: str | None = None,
) -> str:
    selected_locale = normalize_locale(locale or get_configured_locale())
    page = _MENU_PAGE_BY_ID[page_id]
    lines = [_localized(page.title, selected_locale)]
    lines.extend(
        _render_page_body(page, context, selected_locale, include_self_title=False)
    )

    if len(lines) == 1:
        lines.append(
            _localized(
                LocalizedText("暂无可用功能", "No available features"),
                selected_locale,
            )
        )

    return "\n".join(lines)


def default_menu_context() -> MenuRuntimeContext:
    return MenuRuntimeContext(
        platform_id=QQ_PLATFORM_ID,
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        platform_capabilities=QQ_CAPABILITIES,
    )


def qq_menu_context(
    *,
    adapter_id: str,
    implementation_name: str | None = None,
    implementation_version: str | None = None,
    protocol_version: str | None = None,
) -> MenuRuntimeContext:
    return MenuRuntimeContext(
        platform_id=QQ_PLATFORM_ID,
        adapter_id=adapter_id,
        implementation_name=implementation_name,
        implementation_version=implementation_version,
        protocol_version=protocol_version,
        platform_capabilities=QQ_CAPABILITIES,
    )


def _render_section(
    section: MenuSection,
    context: MenuRuntimeContext,
    locale: str,
) -> list[str]:
    title = _localized(section.title, locale)
    lines = [f"【{title}】"]

    for feature in _features_for_section(section.id):
        rendered = _render_feature(feature, context, locale)
        if rendered:
            lines.append(rendered)

    if len(lines) == 1:
        return []
    return lines


def _render_page_body(
    page: MenuPage,
    context: MenuRuntimeContext,
    locale: str,
    *,
    include_self_title: bool,
) -> list[str]:
    lines: list[str] = []
    section = _render_section(MenuSection(page.id, page.title), context, locale)
    if section:
        if include_self_title:
            lines.extend(("", *section))
        else:
            lines.extend(section[1:])

    for child in page.children:
        child_lines = _render_page_body(
            child,
            context,
            locale,
            include_self_title=True,
        )
        if child_lines:
            lines.extend(child_lines)

    return lines


def _page_has_visible_content(page: MenuPage, context: MenuRuntimeContext) -> bool:
    return any(
        _matched_availability(feature, context) for feature in _page_features(page)
    )


def _page_features(page: MenuPage) -> Iterable[MenuFeature]:
    yield from _features_for_section(page.id)
    for child in page.children:
        yield from _page_features(child)


def _features_for_section(section_id: str) -> Iterable[MenuFeature]:
    return (feature for feature in MENU_FEATURES if feature.section_id == section_id)


def _render_feature(
    feature: MenuFeature,
    context: MenuRuntimeContext,
    locale: str,
) -> str:
    availability = _matched_availability(feature, context)
    if availability is None:
        return ""

    command_key = feature.command_key
    trigger = COMMAND_TRIGGERS[command_key]
    command = trigger.primary_for(locale)
    usage = _localized(availability.usage_override or feature.usage, locale)
    summary = _localized(feature.summary, locale)
    command_text = f"{command} {usage}".strip()
    return f"- {summary}: {command_text}"


def _localized(value: Any, locale: str) -> str:
    if isinstance(value, LocalizedText):
        return value.en_us if locale.lower().startswith("en") else value.zh_cn
    if isinstance(value, dict):
        if locale.lower().startswith("en"):
            result = value.get("en_US") or value.get("en") or value.get("zh_CN")
        else:
            result = value.get("zh_CN") or value.get("zh") or value.get("en_US")
        return str(result or "")
    if value is None:
        return ""
    return str(value)


def _matched_availability(
    feature: MenuFeature,
    context: MenuRuntimeContext,
) -> MenuAvailability | None:
    if feature.command_key not in COMMAND_TRIGGERS:
        logger.debug(f"Lingchu 菜单跳过未知命令: {feature.command_key!r}")
        return None
    if feature.platform_capability not in context.platform_capabilities:
        return None
    for availability in feature.availability:
        if _availability_matches(availability, context):
            return availability
    return None


def _availability_matches(
    availability: MenuAvailability,
    context: MenuRuntimeContext,
) -> bool:
    if (
        availability.platform_id != context.platform_id
        or availability.adapter_id != context.adapter_id
    ):
        return False
    context_values = (
        (availability.protocol_version, context.protocol_version),
        (availability.implementation_name, context.implementation_name),
    )
    if any(
        expected is not None and expected != actual
        for expected, actual in context_values
    ):
        return False
    if availability.minimum_version is None:
        return True
    return context.implementation_version is not None and _version_gte(
        context.implementation_version, availability.minimum_version
    )


def _version_gte(current: str, minimum: str) -> bool:
    try:
        current_version: Version = parse(current)
        minimum_version: Version = parse(minimum)
    except InvalidVersion:
        return False
    return current_version >= minimum_version


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
