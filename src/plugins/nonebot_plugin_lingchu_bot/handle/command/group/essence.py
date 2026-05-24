from typing import Any

from arclet.alconna import Alconna, Args
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from ....i18n import _async as _
from .common import run_group_action

set_group_essence_message_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群精华消息", Args["message_seq", int]["is_set?", bool, True]),
    aliases={"设置精华消息", "设为群精华", "设精华"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
unset_group_essence_message_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("取消群精华消息", Args["message_seq", int]),
    aliases={"取消精华消息", "取消群精华", "取消精华"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


@set_group_essence_message_cmd.handle()
async def milkybot_set_group_essence_message(
    message_seq: int,
    is_set: bool,  # noqa: FBT001
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    """
    为指定群消息设置或取消精华并返回操作结果文本。
    
    Parameters:
    	message_seq (int): 目标消息在群内的序列号。
    	is_set (bool): 为 True 时设置为精华，为 False 时取消精华。
    	# bot 与 event 为注入的运行时对象，无需文档化。
    
    Returns:
    	result (str): 描述已执行操作的结果文本（例如 "设置群精华消息: {message_seq}" 或 "取消群精华消息: {message_seq}"）。
    """
    action_text = await _("设置") if is_set else await _("取消")
    return await run_group_action(
        set_group_essence_message_cmd,
        await _("设置群精华消息"),
        lambda: bot.set_group_essence_message(
            group_id=event.data.peer_id, message_seq=message_seq, is_set=is_set
        ),
        (await _("{action}群精华消息: {message_seq}")).format(
            action=action_text, message_seq=message_seq
        ),
    )


@unset_group_essence_message_cmd.handle()
async def milkybot_unset_group_essence_message(
    message_seq: int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    """
    取消指定群消息的精华状态。
    
    Parameters:
        message_seq (int): 要取消精华的群消息的序号（message sequence）。
    
    Returns:
        Any: 格式化的操作结果文本，表示取消操作的结果（成功或失败信息）。
    """
    return await milkybot_set_group_essence_message(
        message_seq=message_seq, is_set=False, bot=bot, event=event
    )
