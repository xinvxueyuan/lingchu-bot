from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

from ......core.runtime_config import get_handle_config_manager
from ......i18n import _async as _
from ......services.llm import LLMError, complete_chat
from ....commands.chat import chat_cmd
from ....commands.common import selected_adapter_handle


@selected_adapter_handle(chat_cmd, "~onebot.v11", "chat")
async def onebot11_chat(
    text: list[str],
    bot: OneBot11,  # noqa: ARG001
    event: OneBot11GroupMessageEvent,  # noqa: ARG001
) -> None:
    config = await get_handle_config_manager().get_config("chat")
    if not config.enabled:
        await chat_cmd.finish(await _("该功能已禁用"))
        return

    system_prompt = config.defaults.get("system_prompt", "你是一个友好的群聊助手。")
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": " ".join(text)})

    try:
        response = await complete_chat(messages)
    except LLMError as exc:
        logger.error(f"Chat LLM call failed: {exc!r}")
        await chat_cmd.finish(await _("LLM 服务暂时不可用，请稍后再试"))
        return

    await chat_cmd.finish(response)
