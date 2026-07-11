"""LLM chat command and OneBot V11 handler."""

from arclet.alconna import Alconna, Args, Nargs
from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11
from nonebot.adapters.onebot.v11.event import GroupMessageEvent

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from ....handle.qq.commands.triggers import COMMAND_TRIGGERS
from ....services.llm import LLMError, complete_chat
from ..contracts import selected_adapter_handle
from .config import get_chat_config
from .i18n import translate

_CHAT = COMMAND_TRIGGERS["chat"]

chat_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_CHAT.primary, Args["text", Nargs(str)]),
    aliases=_CHAT.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


@selected_adapter_handle(chat_cmd, "~onebot.v11", "chat")
async def onebot11_chat(
    text: list[str],
    bot: OneBot11,  # noqa: ARG001
    event: GroupMessageEvent,  # noqa: ARG001
) -> None:
    config = get_chat_config()
    if not config.enabled:
        await chat_cmd.finish(translate("disabled"))
        return

    system_prompt = config.system_prompt
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": " ".join(text)})

    try:
        response = await complete_chat(messages)
    except LLMError as exc:
        logger.error(f"Chat LLM call failed: {exc!r}")
        await chat_cmd.finish(translate("llm_error"))
        return

    await chat_cmd.finish(response)
