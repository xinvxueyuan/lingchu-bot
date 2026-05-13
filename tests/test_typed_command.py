from enum import Enum
from typing import Annotated, Any

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.utils.typed_command import (
    CommandRouter,
    Context,
)


@pytest.mark.asyncio
async def test_dispatch_injects_ctx_parameter() -> None:
    router = CommandRouter()
    captured: dict[str, Any] = {}

    @router.command(path="ping")
    async def ping(ctx: Context, value: int) -> dict[str, Any]:
        raw = ctx.get("raw_text", "")
        captured["raw_text"] = raw
        return {"value": value, "raw_text": raw}

    context: Context = {"raw_text": "ping 1"}
    result = await router.dispatch("ping 1", context=context)

    assert result == {"value": 1, "raw_text": "ping 1"}
    assert captured["raw_text"] == "ping 1"


@pytest.mark.asyncio
async def test_dispatch_injects_underscore_ctx_parameter() -> None:
    router = CommandRouter()
    captured: dict[str, Any] = {}

    @router.command(path="mute")
    async def mute(_ctx: Context, value: int) -> dict[str, Any]:
        raw = _ctx.get("raw_text", "")
        captured["raw_text"] = raw
        return {"value": value, "raw_text": raw}

    context: Context = {"raw_text": "mute 2"}
    result = await router.dispatch("mute 2", context=context)

    assert result == {"value": 2, "raw_text": "mute 2"}
    assert captured["raw_text"] == "mute 2"


def test_help_includes_annotated_description() -> None:
    router = CommandRouter()

    @router.command(path="who")
    def who(user: Annotated[int, "user", "支持 @用户"]) -> str:
        """查询用户信息"""
        _ = user
        return "ok"

    help_text = router.help()
    assert "支持 @用户" in help_text


class SegmentKind(Enum):
    TEXT = "text"
    MENTION = "mention"


@pytest.mark.asyncio
async def test_dispatch_parses_enum_parameter() -> None:
    router = CommandRouter()

    @router.command(path="segment")
    async def segment(kind: SegmentKind) -> SegmentKind:
        return kind

    result = await router.dispatch("segment text")

    assert result == SegmentKind.TEXT


@pytest.mark.asyncio
async def test_dispatch_parses_json_payload() -> None:
    router = CommandRouter()

    @router.command(path="send")
    async def send(payload: Annotated[dict, "json"]) -> Any:
        return payload

    result = await router.dispatch('send {"type":"text","data":{"text":"Hello"}}')

    assert result == {"type": "text", "data": {"text": "Hello"}}


def test_parse_rejects_invalid_json() -> None:
    router = CommandRouter()

    @router.command(path="send")
    def send(payload: Annotated[dict, "json"]) -> Any:
        return payload

    result = router.parse("send {bad}")

    assert result.get("error") is True
    assert result.get("expected") == "json"
