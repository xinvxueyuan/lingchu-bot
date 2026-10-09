"""LLBot 私有层：``get_group_shut_list`` 调用与响应解析。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.llbot import (
    mute_list as llbot_mute_list,
)


def test_parse_muted_members_llbot_payload() -> None:
    """LLBot 的 data 数组解析为 MutedMember；cardName 优先于 nick。"""
    payload = {
        "status": "ok",
        "retcode": 0,
        "data": [
            {
                "uin": "10001",
                "uid": "u_a",
                "nick": "甲",
                "cardName": "",
                "role": 2,
                "shutUpTime": 1750385481,
                "isRobot": False,
            },
            {
                "uin": "10002",
                "uid": "u_b",
                "nick": "乙",
                "cardName": "乙的群名片",
                "role": 3,
                "shutUpTime": 1750390000,
                "isRobot": False,
            },
        ],
    }
    members = llbot_mute_list.parse_muted_members(payload)

    assert [m.user_id for m in members] == [10001, 10002]
    assert members[0].display_name == "甲"
    assert members[1].display_name == "乙的群名片"
    assert members[1].shut_up_time == 1750390000


def test_parse_muted_members_skips_bad_rows() -> None:
    """缺 uin / uin 非数字 / bool 的行被跳过，不影响其它行。"""
    payload = {
        "retcode": 0,
        "data": [
            {"uin": "10001", "nick": "甲"},
            {"nick": "没有 uin"},
            {"uin": "not-a-number", "nick": "坏值"},
            {"uin": 10004, "nick": "丙"},
            {"uin": None, "nick": "空值"},
            {"uin": True, "nick": "布尔"},
        ],
    }
    members = llbot_mute_list.parse_muted_members(payload)

    assert [m.user_id for m in members] == [10001, 10004]


def test_parse_muted_members_tolerates_wrong_shapes() -> None:
    """非 dict / data 非 list / data 缺失都返回空列表，不抛异常。"""
    for bad in (None, [], "x", {}, {"data": None}, {"data": "x"}, {"data": {}}, 0):
        assert llbot_mute_list.parse_muted_members(bad) == []


def test_parse_muted_members_display_name_falls_back_to_uin() -> None:
    """Nick 与 cardName 都缺时用 uin 兜底，不留空名字。"""
    payload = {"data": [{"uin": "10001"}, {"uin": "10002", "nick": "   "}]}
    members = llbot_mute_list.parse_muted_members(payload)

    assert [m.display_name for m in members] == ["10001", "10002"]


def test_parse_muted_members_shut_up_time_non_int() -> None:
    """ShutUpTime 非 int（缺失/字符串）记为 None，不猜。"""
    payload = {"data": [{"uin": "1"}, {"uin": "2", "shutUpTime": "abc"}]}
    members = llbot_mute_list.parse_muted_members(payload)

    assert [m.shut_up_time for m in members] == [None, None]


@pytest.mark.asyncio
async def test_fetch_group_shut_list_calls_private_action() -> None:
    """调用私有 action 名 get_group_shut_list（**不带**前导下划线）。

    mock 用真实契约：适配器 ``handle_api_result`` 会解包顶层 ``data``，
    ``call_api`` 返回的就是成员数组本身。
    """
    bot = MagicMock()
    bot.call_api = AsyncMock(return_value=[{"uin": "1"}])

    members = await llbot_mute_list.fetch_group_shut_list(bot=bot, group_id=999)

    bot.call_api.assert_awaited_once_with("get_group_shut_list", group_id=999)
    assert [m.user_id for m in members] == [1]


def test_adapter_unwraps_data_field() -> None:
    """契约守卫：适配器确实解包 ``data``。

    这条钉住的是「mock 该返回什么形状」这一前提。若 nonebot 改变解包行为，
    这条会失败，提醒我们同步所有 mock 与解析逻辑（否则测试会在现实中失效）。
    """
    from nonebot.adapters.onebot.v11.utils import handle_api_result

    rows = [{"uin": "1"}]
    assert handle_api_result({"status": "ok", "retcode": 0, "data": rows}) is rows
    assert handle_api_result({"status": "ok", "retcode": 0, "data": []}) == []


@pytest.mark.asyncio
async def test_fetch_group_shut_list_accepts_unwrapped_payload() -> None:
    """真实形态（适配器已解包）：数组直接可用，不会误判成「没有被禁言」。"""
    bot = MagicMock()
    bot.call_api = AsyncMock(
        return_value=[{"uin": "10001", "nick": "甲"}, {"uin": "10002", "nick": "乙"}]
    )

    members = await llbot_mute_list.fetch_group_shut_list(bot=bot, group_id=999)

    assert [m.user_id for m in members] == [10001, 10002]
    assert [m.display_name for m in members] == ["甲", "乙"]


@pytest.mark.asyncio
async def test_fetch_group_shut_list_accepts_envelope_payload() -> None:
    """防御性兼容：万一拿到未解包的信封也能解析。"""
    bot = MagicMock()
    bot.call_api = AsyncMock(
        return_value={"status": "ok", "retcode": 0, "data": [{"uin": "10001"}]}
    )

    members = await llbot_mute_list.fetch_group_shut_list(bot=bot, group_id=999)

    assert [m.user_id for m in members] == [10001]


def test_parse_muted_members_accepts_both_shapes() -> None:
    """解析函数对「数组」与「信封」两种形状都给出一致结果。"""
    rows = [{"uin": "10001", "nick": "甲"}, {"uin": "10002", "nick": "乙"}]

    assert llbot_mute_list.parse_muted_members(rows) == (
        llbot_mute_list.parse_muted_members({"retcode": 0, "data": rows})
    )


def test_llbot_action_name_has_no_leading_underscore() -> None:
    """钉住 action 名：LLBot 的这个接口无前导下划线。"""
    assert llbot_mute_list.GET_GROUP_SHUT_LIST_ACTION == "get_group_shut_list"
    assert not llbot_mute_list.GET_GROUP_SHUT_LIST_ACTION.startswith("_")
    assert llbot_mute_list.LLBOT_APP_NAME == "LLOneBot"
