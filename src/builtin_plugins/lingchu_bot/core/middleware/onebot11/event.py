from copy import deepcopy
from typing import Any, Literal

from nonebot.adapters.onebot.compat import model_validator
from nonebot.adapters.onebot.v11 import Event, Message
from nonebot.adapters.onebot.v11.adapter import Adapter
from nonebot.adapters.onebot.v11.event import Reply, Sender

add_custom_model = Adapter.add_custom_model


class MessageSentEvent(Event):
    """自我消息事件"""

    post_type: Literal["message_sent"]  # type: ignore[override]
    sub_type: str
    user_id: int
    message_type: str
    message_id: int
    message: Message
    original_message: Message
    raw_message: str
    font: int
    sender: Sender
    to_me: bool = False
    reply: Reply | None = None

    @model_validator(mode="before")
    @classmethod
    def check_message(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "message" in values:
            values["original_message"] = deepcopy(values["message"])
        return values

    def get_event_name(self) -> str:
        sub_type = getattr(self, "sub_type", None)
        return f"{self.post_type}.{self.message_type}" + (
            f".{sub_type}" if sub_type else ""
        )

    def get_message(self) -> Message:
        return self.message

    def get_user_id(self) -> str:
        return str(self.user_id)

    def get_session_id(self) -> str:
        return str(self.user_id)

    def is_tome(self) -> bool:
        return self.to_me


add_custom_model(MessageSentEvent)
