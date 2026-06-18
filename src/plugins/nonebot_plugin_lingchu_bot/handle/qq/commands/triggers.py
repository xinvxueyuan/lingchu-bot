from dataclasses import dataclass

from ....i18n import get_configured_locale, normalize_locale


@dataclass(frozen=True)
class CommandTrigger:
    chinese: str
    english: str
    chinese_aliases: frozenset[str]
    english_aliases: frozenset[str]

    def primary_for(self, locale: str | None = None) -> str:
        if _is_english_locale(locale):
            return self.english
        return self.chinese

    def aliases_for(self, locale: str | None = None) -> set[str]:
        if _is_english_locale(locale):
            return set(self.english_aliases)
        return set(self.chinese_aliases)

    @property
    def primary(self) -> str:
        return self.primary_for()

    @property
    def aliases(self) -> set[str]:
        return self.aliases_for()


def _is_english_locale(locale: str | None = None) -> bool:
    configured_locale = get_configured_locale() if locale is None else locale
    return normalize_locale(configured_locale).lower().startswith("en")


COMMAND_TRIGGERS = {
    "menu": CommandTrigger(
        chinese="菜单",
        english="menu",
        chinese_aliases=frozenset({"帮助", "功能", "功能列表", "指令", "命令列表"}),
        english_aliases=frozenset({"help", "commands"}),
    ),
    "member_mute": CommandTrigger(
        chinese="禁言",
        english="mute",
        chinese_aliases=frozenset({"禁言用户", "禁言群成员", "禁言成员", "禁", "封禁"}),
        english_aliases=frozenset({"ban", "mute-member", "ban-member"}),
    ),
    "member_unmute": CommandTrigger(
        chinese="解禁",
        english="unmute",
        chinese_aliases=frozenset(
            {
                "解禁用户",
                "解禁群成员",
                "解禁成员",
                "解禁",
                "解封",
                "解除封禁",
                "解除禁言",
            }
        ),
        english_aliases=frozenset({"pardon", "unmute-member"}),
    ),
    "whole_mute": CommandTrigger(
        chinese="全员禁言",
        english="mute-all",
        chinese_aliases=frozenset(
            {
                "开启全体禁言",
                "全禁",
                "全禁言",
                "全体禁言",
                "全体禁言开启",
                "全员禁言开启",
                "开启全员禁言",
                "禁言群",
            }
        ),
        english_aliases=frozenset({"mute-group", "enable-whole-mute"}),
    ),
    "whole_unmute": CommandTrigger(
        chinese="全体解禁",
        english="unmute-all",
        chinese_aliases=frozenset(
            {
                "全员解禁",
                "关闭全体禁言",
                "解除全体禁言",
                "解禁全体",
                "解禁全员",
                "全解",
                "全解禁",
                "全体解禁",
                "关闭全员禁言",
                "解除全员禁言",
                "解禁群",
            }
        ),
        english_aliases=frozenset({"unmute-group", "disable-whole-mute"}),
    ),
    "set_group_name": CommandTrigger(
        chinese="设置群名称",
        english="set-group-name",
        chinese_aliases=frozenset({"改群名", "修改群名称", "设置群名"}),
        english_aliases=frozenset({"rename-group"}),
    ),
    "set_group_avatar": CommandTrigger(
        chinese="设置群头像",
        english="set-group-avatar",
        chinese_aliases=frozenset({"改群头像", "修改群头像"}),
        english_aliases=frozenset({"change-group-avatar"}),
    ),
    "set_member_card": CommandTrigger(
        chinese="设置群名片",
        english="set-member-card",
        chinese_aliases=frozenset({"改群名片", "修改群名片", "设置成员名片"}),
        english_aliases=frozenset({"set-group-card"}),
    ),
    "set_member_title": CommandTrigger(
        chinese="设置群头衔",
        english="set-member-title",
        chinese_aliases=frozenset({"设置专属头衔", "设置群成员专属头衔", "改群头衔"}),
        english_aliases=frozenset({"set-special-title"}),
    ),
    "set_member_admin": CommandTrigger(
        chinese="设置群管理员",
        english="set-member-admin",
        chinese_aliases=frozenset({"设置管理员", "任命群管理员"}),
        english_aliases=frozenset({"set-admin", "promote-admin"}),
    ),
    "unset_member_admin": CommandTrigger(
        chinese="取消群管理员",
        english="unset-member-admin",
        chinese_aliases=frozenset({"取消管理员", "撤销群管理员"}),
        english_aliases=frozenset({"unset-admin", "revoke-admin"}),
    ),
    "kick_member": CommandTrigger(
        chinese="踢出群成员",
        english="kick-member",
        chinese_aliases=frozenset({"踢出", "踢人", "移出群成员"}),
        english_aliases=frozenset({"kick", "remove-member"}),
    ),
    "block_member": CommandTrigger(
        chinese="拉黑",
        english="block",
        chinese_aliases=frozenset({"拉黑用户"}),
        english_aliases=frozenset({"block-member"}),
    ),
    "global_block_member": CommandTrigger(
        chinese="全局拉黑",
        english="global-block",
        chinese_aliases=frozenset({"全局拉黑用户"}),
        english_aliases=frozenset({"global-block-member"}),
    ),
    "unblock_member": CommandTrigger(
        chinese="删黑",
        english="unblock",
        chinese_aliases=frozenset({"删除黑名单"}),
        english_aliases=frozenset({"unblock-member"}),
    ),
    "global_unblock_member": CommandTrigger(
        chinese="全局删黑",
        english="global-unblock",
        chinese_aliases=frozenset({"全局删除黑名单"}),
        english_aliases=frozenset({"global-unblock-member"}),
    ),
    "clear_blocklist": CommandTrigger(
        chinese="清空黑名单",
        english="clear-blocklist",
        chinese_aliases=frozenset(),
        english_aliases=frozenset(),
    ),
    "global_clear_blocklist": CommandTrigger(
        chinese="全局清空黑名单",
        english="global-clear-blocklist",
        chinese_aliases=frozenset(),
        english_aliases=frozenset(),
    ),
    "send_announcement": CommandTrigger(
        chinese="发送群公告",
        english="send-announcement",
        chinese_aliases=frozenset({"发群公告", "群公告"}),
        english_aliases=frozenset({"announce", "group-announcement"}),
    ),
    "leave_group": CommandTrigger(
        chinese="退出群",
        english="leave-group",
        chinese_aliases=frozenset({"退群", "退出当前群"}),
        english_aliases=frozenset({"quit-group"}),
    ),
    "remote_mute": CommandTrigger(
        chinese="远程禁言",
        english="remote-mute",
        chinese_aliases=frozenset({"跨群禁言", "远程禁言用户", "远程禁言成员"}),
        english_aliases=frozenset({"remote-ban", "cross-group-mute"}),
    ),
    "remote_unmute": CommandTrigger(
        chinese="远程解禁",
        english="remote-unmute",
        chinese_aliases=frozenset({"跨群解禁", "远程解禁用户", "远程解禁成员"}),
        english_aliases=frozenset({"remote-pardon", "cross-group-unmute"}),
    ),
    "remote_whole_mute": CommandTrigger(
        chinese="远程全体禁言",
        english="remote-mute-all",
        chinese_aliases=frozenset({"跨群全体禁言", "远程全员禁言", "远程开启全体禁言"}),
        english_aliases=frozenset({"remote-mute-group", "cross-group-mute-all"}),
    ),
    "remote_whole_unmute": CommandTrigger(
        chinese="远程全体解禁",
        english="remote-unmute-all",
        chinese_aliases=frozenset({"跨群全体解禁", "远程全员解禁", "远程关闭全体禁言"}),
        english_aliases=frozenset({"remote-unmute-group", "cross-group-unmute-all"}),
    ),
    "remote_kick": CommandTrigger(
        chinese="远程踢出",
        english="remote-kick",
        chinese_aliases=frozenset({"跨群踢出", "远程踢人", "远程移出群成员"}),
        english_aliases=frozenset({"remote-kick-member", "cross-group-kick"}),
    ),
    "remote_block": CommandTrigger(
        chinese="远程拉黑",
        english="remote-block",
        chinese_aliases=frozenset({"跨群拉黑", "远程拉黑用户"}),
        english_aliases=frozenset({"remote-block-member", "cross-group-block"}),
    ),
    "remote_unblock": CommandTrigger(
        chinese="远程删黑",
        english="remote-unblock",
        chinese_aliases=frozenset({"跨群删黑", "远程删除黑名单"}),
        english_aliases=frozenset({"remote-unblock-member", "cross-group-unblock"}),
    ),
    "remote_announcement": CommandTrigger(
        chinese="远程公告",
        english="remote-announcement",
        chinese_aliases=frozenset({"跨群公告", "远程群公告", "远程发公告"}),
        english_aliases=frozenset({"remote-notice", "cross-group-announcement"}),
    ),
}
