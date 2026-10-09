"""LLBot 私有的群禁言名单接口（``get_group_shut_list``）。

该 action 不在 OneBot V11 标准 API 面内，只有 LLBot 提供，因此本模块位于
**私有层**：由 ``default/mute.py`` 的中间层按协议端解析并分派后再调用。

对应文档：<https://api.luckylillia.com/api-311303893>
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot

#: LLBot 在 ``get_version_info().app_name`` 中上报的标识（生产实测值）。
LLBOT_APP_NAME = "LLOneBot"

#: LLBot 私有的群禁言名单 action（**无**前导下划线）。
#: 与 ``_get_group_notice`` 那批不同：带下划线是为了和 go-cqhttp 同名接口区分，
#: 这个不是同名接口。
GET_GROUP_SHUT_LIST_ACTION = "get_group_shut_list"


@dataclass(frozen=True)
class MutedMember:
    """一名当前被禁言的群成员。"""

    user_id: int
    display_name: str
    shut_up_time: int | None = None


def parse_muted_members(payload: Any) -> list[MutedMember]:
    """把 ``get_group_shut_list`` 的响应解析成成员列表。

    响应形状::

        {"status": "ok", "retcode": 0,
         "data": [{"uin": "123", "uid": "u_...", "nick": "...", "cardName": "...",
                   "role": 2, "shutUpTime": 1750385481, "isRobot": false}]}

    缺字段或 ``uin`` 非数字的行直接跳过 —— 一行坏数据不该让整条命令失败。
    非 dict / ``data`` 非 list 的形状一律返回空列表，不抛异常。
    """
    if not isinstance(payload, dict):
        return []
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    members: list[MutedMember] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_uin = row.get("uin")
        if raw_uin is None or isinstance(raw_uin, bool):
            continue
        try:
            user_id = int(raw_uin)
        except (TypeError, ValueError):
            continue
        card_name = str(row.get("cardName") or "").strip()
        nick = str(row.get("nick") or "").strip() or str(user_id)
        shut_up = row.get("shutUpTime")
        members.append(
            MutedMember(
                user_id=user_id,
                display_name=card_name or nick,
                shut_up_time=shut_up if isinstance(shut_up, int) else None,
            )
        )
    return members


async def fetch_group_shut_list(
    *,
    bot: OneBot11Bot,
    group_id: int,
) -> list[MutedMember]:
    """取指定群的被禁言成员（LLBot 私有接口）。

    异常由调用方（``default/mute.py`` 中间层）处理：私有接口在别的协议端上会
    返回 ``ActionFailed``，中间层负责把它翻成用户可读的「不支持」。
    """
    payload = await bot.call_api(GET_GROUP_SHUT_LIST_ACTION, group_id=group_id)
    return parse_muted_members(payload)
