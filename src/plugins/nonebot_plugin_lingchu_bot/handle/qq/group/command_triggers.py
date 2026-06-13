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
}
