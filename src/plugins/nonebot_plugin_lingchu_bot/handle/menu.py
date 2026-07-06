from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from arclet.alconna import Alconna
from nonebot import logger
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from packaging.version import InvalidVersion, Version, parse

from ..core.runtime_config import runtime_config
from ..i18n import _async as _
from ..i18n import get_configured_locale, gettext, normalize_locale
from ..platforms import QQ_CAPABILITIES, PlatformCapability, resolve_enabled_adapters
from .qq.adapters import load_adapter_handlers
from .qq.commands.triggers import COMMAND_TRIGGERS

if TYPE_CHECKING:
    from collections.abc import Iterable

_MENU = COMMAND_TRIGGERS["menu"]
QQ_PLATFORM_ID: Final = "qq"
ONEBOT_V11_ADAPTER_ID: Final = "~onebot.v11"
NAPCAT_IMPL: Final = "NapCat.Onebot"

menu_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_MENU.primary),
    aliases=_MENU.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_ADAPTER_MODULES: dict[str, tuple[str, ...]] = {
    "~onebot.v11": (".qq.adapters.onebot11.default.menu",),
}


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


_DEFAULT_MENU_PAGES: Final[tuple[MenuPage, ...]] = (
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
    MenuPage(
        "remote-management",
        LocalizedText("远程管理", "Remote Management"),
        command=LocalizedText("远程管理", "remote-management"),
    ),
    MenuPage(
        "system-management",
        LocalizedText("系统管理", "System Management"),
        children=(
            MenuPage("silent-mode", LocalizedText("静默模式", "Silent Mode")),
            MenuPage("handle-gate", LocalizedText("开关机", "Handle Gate")),
            MenuPage(
                "application-operation",
                LocalizedText("应用端操作", "Application Operation"),
            ),
        ),
        command=LocalizedText("系统管理", "system-management"),
    ),
    MenuPage(
        "entertainment",
        LocalizedText("娱乐功能", "Entertainment"),
        command=LocalizedText("娱乐功能", "entertainment"),
    ),
)
MENU_PAGES: tuple[MenuPage, ...] = _DEFAULT_MENU_PAGES


def _flatten_pages(pages: Iterable[MenuPage]) -> tuple[MenuPage, ...]:
    result: list[MenuPage] = []
    for page in pages:
        result.append(page)
        result.extend(_flatten_pages(page.children))
    return tuple(result)


def _sections_from_pages(pages: tuple[MenuPage, ...]) -> tuple[MenuSection, ...]:
    return tuple(MenuSection(page.id, page.title) for page in pages)


def _page_commands_from_pages(pages: tuple[MenuPage, ...]) -> tuple[MenuPage, ...]:
    return tuple(page for page in pages if page.command is not None)


def _page_lookup_from_pages(pages: tuple[MenuPage, ...]) -> dict[str, MenuPage]:
    return {page.id: page for page in _flatten_pages(pages)}


MENU_SECTIONS: tuple[MenuSection, ...] = _sections_from_pages(MENU_PAGES)
MENU_PAGE_COMMANDS: tuple[MenuPage, ...] = _page_commands_from_pages(MENU_PAGES)
_MENU_PAGE_BY_ID: dict[str, MenuPage] = _page_lookup_from_pages(MENU_PAGES)


def _menu_page_command(page: MenuPage) -> str:
    command = page.command
    if command is None:
        return ""
    locale = normalize_locale(get_configured_locale())
    override = runtime_config.menu_page_trigger_overrides.get(page.id, {})
    if locale.lower().startswith("en"):
        value = override.get("english") if isinstance(override, dict) else None
        return str(value).strip() if value else command.en_us
    value = override.get("chinese") if isinstance(override, dict) else None
    return str(value).strip() if value else command.zh_cn


menu_page_cmds: Final[dict[str, type[AlconnaMatcher]]] = {
    page.id: on_alconna(
        command=Alconna(_menu_page_command(page)),
        priority=5,
        block=True,
        use_cmd_sep=True,
        use_cmd_start=True,
    )
    for page in _page_commands_from_pages(_DEFAULT_MENU_PAGES)
}

_QQ_BOTH: Final[tuple[MenuAvailability, ...]] = (
    MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),
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
_ONEBOT_ANNOUNCEMENT: Final[tuple[MenuAvailability, ...]] = _ONEBOT_NAPCAT

_DEFAULT_MENU_FEATURES: Final[tuple[MenuFeature, ...]] = (
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
        "block-member",
        "block_member",
        "member-management",
        LocalizedText("拉黑群成员", "Block a group member"),
        LocalizedText("@用户 [时长秒数] [原因]", "@user [duration seconds] [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "global-block-member",
        "global_block_member",
        "member-management",
        LocalizedText("全局拉黑群成员", "Globally block a group member"),
        LocalizedText("@用户 [时长秒数] [原因]", "@user [duration seconds] [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "unblock-member",
        "unblock_member",
        "member-management",
        LocalizedText("删除本群黑名单", "Remove a group blocklist entry"),
        LocalizedText("@用户 [原因]", "@user [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "global-unblock-member",
        "global_unblock_member",
        "member-management",
        LocalizedText("删除全局黑名单", "Remove a global blocklist entry"),
        LocalizedText("@用户 [原因]", "@user [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "clear-blocklist",
        "clear_blocklist",
        "member-management",
        LocalizedText("清空本群黑名单", "Clear current group blocklist"),
        LocalizedText("[原因]", "[reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "global-clear-blocklist",
        "global_clear_blocklist",
        "member-management",
        LocalizedText("清空全局黑名单", "Clear global blocklist"),
        LocalizedText("[原因]", "[reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "protect-member",
        "protect_member",
        "member-management",
        LocalizedText("拉白群成员", "Protect a group member"),
        LocalizedText("@用户 [原因]", "@user [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "global-protect-member",
        "global_protect_member",
        "member-management",
        LocalizedText("全局拉白群成员", "Globally protect a group member"),
        LocalizedText("@用户 [原因]", "@user [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "unprotect-member",
        "unprotect_member",
        "member-management",
        LocalizedText("删除本群白名单", "Remove a group whitelist entry"),
        LocalizedText("@用户 [原因]", "@user [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "global-unprotect-member",
        "global_unprotect_member",
        "member-management",
        LocalizedText("删除全局白名单", "Remove a global whitelist entry"),
        LocalizedText("@用户 [原因]", "@user [reason]"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
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
        LocalizedText("@用户", "@user"),
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
        "recall-message",
        "recall_message",
        "speech-management",
        LocalizedText("撤回群消息", "Recall group messages"),
        LocalizedText("[@用户] [数量]", "[@user] [count]"),
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
        (*_ONEBOT_NAPCAT,),
    ),
    MenuFeature(
        "send-announcement",
        "send_announcement",
        "announcement",
        LocalizedText("发送群公告", "Send group announcement"),
        LocalizedText("<内容> [图片]", "<content> [image]"),
        PlatformCapability.ANNOUNCEMENT,
        (*_ONEBOT_ANNOUNCEMENT,),
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
    MenuFeature(
        "remote-mute",
        "remote_mute",
        "remote-management",
        LocalizedText("远程禁言", "Remote mute"),
        LocalizedText(
            "<群号|群名称> @用户 [时长秒数] [原因]",
            "<group_id|group_name> @user [duration seconds] [reason]",
        ),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "remote-unmute",
        "remote_unmute",
        "remote-management",
        LocalizedText("远程解禁", "Remote unmute"),
        LocalizedText(
            "<群号|群名称> @用户 [原因]",
            "<group_id|group_name> @user [reason]",
        ),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "remote-whole-mute",
        "remote_whole_mute",
        "remote-management",
        LocalizedText("远程全体禁言", "Remote whole mute"),
        LocalizedText("<群号|群名称>", "<group_id|group_name>"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "remote-whole-unmute",
        "remote_whole_unmute",
        "remote-management",
        LocalizedText("远程全体解禁", "Remote whole unmute"),
        LocalizedText("<群号|群名称>", "<group_id|group_name>"),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "remote-kick",
        "remote_kick",
        "remote-management",
        LocalizedText("远程踢出", "Remote kick"),
        LocalizedText(
            "<群号|群名称> @用户 [原因]",
            "<group_id|group_name> @user [reason]",
        ),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "remote-block",
        "remote_block",
        "remote-management",
        LocalizedText("远程拉黑", "Remote block"),
        LocalizedText(
            "<群号|群名称> @用户 [时长秒数] [原因]",
            "<group_id|group_name> @user [duration seconds] [reason]",
        ),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "remote-unblock",
        "remote_unblock",
        "remote-management",
        LocalizedText("远程删黑", "Remote unblock"),
        LocalizedText(
            "<群号|群名称> @用户 [原因]",
            "<group_id|group_name> @user [reason]",
        ),
        PlatformCapability.MEMBER_MODERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "remote-announcement",
        "remote_announcement",
        "remote-management",
        LocalizedText("远程公告", "Remote announcement"),
        LocalizedText(
            "<群号|群名称> <内容> [图片]",
            "<group_id|group_name> <content> [image]",
        ),
        PlatformCapability.ANNOUNCEMENT,
        (*_ONEBOT_ANNOUNCEMENT,),
    ),
    MenuFeature(
        "mass-announcement",
        "mass_announcement",
        "remote-management",
        LocalizedText("群发公告", "Mass announcement"),
        LocalizedText(
            "<内容> [群号|群名称列表|全部群] [图片]",
            "<content> [group_ids|group_names|all] [image]",
        ),
        PlatformCapability.ANNOUNCEMENT,
        (*_ONEBOT_ANNOUNCEMENT,),
    ),
    MenuFeature(
        "bot-silence",
        "bot_silence",
        "silent-mode",
        LocalizedText("闭嘴", "Silence"),
        LocalizedText("", ""),
        PlatformCapability.GROUP_MANAGEMENT,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "bot-speak",
        "bot_speak",
        "silent-mode",
        LocalizedText("说话", "Speak"),
        LocalizedText("", ""),
        PlatformCapability.GROUP_MANAGEMENT,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "bot-boot",
        "bot_boot",
        "handle-gate",
        LocalizedText("开机", "Boot"),
        LocalizedText("", ""),
        PlatformCapability.GROUP_MANAGEMENT,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "bot-shutdown",
        "bot_shutdown",
        "handle-gate",
        LocalizedText("关机", "Shutdown"),
        LocalizedText("", ""),
        PlatformCapability.GROUP_MANAGEMENT,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "restart-protocol-endpoint",
        "restart_protocol_endpoint",
        "application-operation",
        LocalizedText("重启协议端", "Restart protocol endpoint"),
        LocalizedText("[平台]", "[platform]"),
        PlatformCapability.APPLICATION_OPERATION,
        (MenuAvailability(QQ_PLATFORM_ID, ONEBOT_V11_ADAPTER_ID),),
    ),
    MenuFeature(
        "chat",
        "chat",
        "entertainment",
        LocalizedText("与 AI 聊天", "Chat with AI"),
        LocalizedText("<文本>", "<text>"),
        PlatformCapability.LLM_CHAT,
        _QQ_BOTH,
    ),
)
MENU_FEATURES: tuple[MenuFeature, ...] = _DEFAULT_MENU_FEATURES


def set_menu_pages(pages: tuple[MenuPage, ...]) -> None:
    """Replace runtime menu pages and refresh derived lookup data."""
    global MENU_PAGES, MENU_PAGE_COMMANDS, MENU_SECTIONS, _MENU_PAGE_BY_ID  # noqa: PLW0603
    MENU_PAGES = pages
    MENU_SECTIONS = _sections_from_pages(pages)
    MENU_PAGE_COMMANDS = _page_commands_from_pages(pages)
    _MENU_PAGE_BY_ID = _page_lookup_from_pages(pages)


def set_menu_features(features: tuple[MenuFeature, ...]) -> None:
    """Replace runtime menu features used by renderers and permissions."""
    global MENU_FEATURES  # noqa: PLW0603
    MENU_FEATURES = features


def render_menu(
    locale: str | None = None,
    context: MenuRuntimeContext | None = None,
    allowed_command_keys: frozenset[str] | None = None,
) -> str:
    return render_menu_index(
        context or default_menu_context(),
        locale,
        allowed_command_keys,
    )


def render_menu_index(
    context: MenuRuntimeContext,
    locale: str | None = None,
    allowed_command_keys: frozenset[str] | None = None,
) -> str:
    selected_locale = normalize_locale(locale or get_configured_locale())
    lines = [gettext("灵初功能菜单", selected_locale)]

    for page in MENU_PAGE_COMMANDS:
        if not _page_has_visible_content(page, context, allowed_command_keys):
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
    allowed_command_keys: frozenset[str] | None = None,
) -> str:
    return render_menu_index(context, locale, allowed_command_keys)


def render_menu_page(
    page_id: str,
    context: MenuRuntimeContext,
    locale: str | None = None,
    allowed_command_keys: frozenset[str] | None = None,
) -> str:
    selected_locale = normalize_locale(locale or get_configured_locale())
    page = _MENU_PAGE_BY_ID[page_id]
    lines = [_localized(page.title, selected_locale)]
    lines.extend(
        _render_page_body(
            page,
            context,
            selected_locale,
            allowed_command_keys=allowed_command_keys,
            include_self_title=False,
        )
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
    allowed_command_keys: frozenset[str] | None = None,
) -> list[str]:
    title = _localized(section.title, locale)
    lines = [f"【{title}】"]

    for feature in _features_for_section(section.id):
        rendered = _render_feature(feature, context, locale, allowed_command_keys)
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
    allowed_command_keys: frozenset[str] | None,
    include_self_title: bool,
) -> list[str]:
    lines: list[str] = []
    section = _render_section(
        MenuSection(page.id, page.title),
        context,
        locale,
        allowed_command_keys,
    )
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
            allowed_command_keys=allowed_command_keys,
            include_self_title=True,
        )
        if child_lines:
            lines.extend(child_lines)

    return lines


def _page_has_visible_content(
    page: MenuPage,
    context: MenuRuntimeContext,
    allowed_command_keys: frozenset[str] | None = None,
) -> bool:
    return any(
        _matched_availability(feature, context, allowed_command_keys)
        for feature in _page_features(page)
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
    allowed_command_keys: frozenset[str] | None = None,
) -> str:
    availability = _matched_availability(feature, context, allowed_command_keys)
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
    allowed_command_keys: frozenset[str] | None = None,
) -> MenuAvailability | None:
    if feature.command_key not in COMMAND_TRIGGERS:
        logger.debug(f"Lingchu 菜单跳过未知命令: {feature.command_key!r}")
        return None
    if (
        allowed_command_keys is not None
        and feature.command_key not in allowed_command_keys
    ):
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


async def import_handle() -> Any:
    for adapter_id in sorted(resolve_enabled_adapters()):
        handlers = load_adapter_handlers(adapter_id, _ADAPTER_MODULES, __package__)
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
