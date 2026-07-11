"""LLM chat command and OneBot V11 handler."""

from arclet.alconna import Alconna, Args, Nargs
from nonebot import logger, require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from ..contracts import (
    SubpluginLLMError,
    complete_subplugin_chat_default,
    get_subplugin_trigger,
    register_subplugin_handler,
)
from .config import get_chat_config
from .i18n import translate

_chat_trigger = get_subplugin_trigger("chat")

chat_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_chat_trigger.primary, Args["text", Nargs(str)]),
    aliases=set(_chat_trigger.aliases),
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


@register_subplugin_handler(chat_cmd, "chat", "~onebot.v11")
async def chat_handler(text: list[str]) -> None:
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
        response = await complete_subplugin_chat_default(messages)
    except SubpluginLLMError as exc:
        logger.error(f"Chat LLM call failed: {exc!r}")
        await chat_cmd.finish(translate("llm_error"))
        return

    await chat_cmd.finish(response)
