"""Handle configuration defaults registry.

This module provides a centralized registry for default configurations
of different handle commands. Each handle can register its default
configuration using the `register_handle_defaults` function.
"""

from typing import Any

HANDLE_DEFAULTS_REGISTRY: dict[str, dict[str, Any]] = {}


def register_handle_defaults(command_key: str, defaults: dict[str, Any]) -> None:
    """Register default configuration for a handle command.

    Args:
        command_key: The unique identifier for the handle command.
        defaults: The default configuration dictionary containing
            'enabled', 'defaults', and 'policies' keys.

    Raises:
        ValueError: If command_key is already registered.
    """
    if command_key in HANDLE_DEFAULTS_REGISTRY:
        raise ValueError(f"duplicate key: {command_key}")  # noqa: TRY003
    HANDLE_DEFAULTS_REGISTRY[command_key] = defaults


# Import and register default configurations
from .block_member import BLOCK_MEMBER_DEFAULTS
from .chat import CHAT_DEFAULTS
from .kick_member import KICK_MEMBER_DEFAULTS
from .mass_announcement import MASS_ANNOUNCEMENT_DEFAULTS
from .member_mute import MEMBER_MUTE_DEFAULTS
from .protect_member import PROTECT_MEMBER_DEFAULTS
from .recall_message import RECALL_MESSAGE_DEFAULTS
from .remote_announcement import REMOTE_ANNOUNCEMENT_DEFAULTS
from .remote_block import REMOTE_BLOCK_DEFAULTS
from .remote_kick import REMOTE_KICK_DEFAULTS
from .remote_mute import REMOTE_MUTE_DEFAULTS
from .restart_protocol_endpoint import RESTART_PROTOCOL_ENDPOINT_DEFAULTS
from .send_announcement import SEND_ANNOUNCEMENT_DEFAULTS
from .set_group_avatar import SET_GROUP_AVATAR_DEFAULTS
from .set_group_name import SET_GROUP_NAME_DEFAULTS
from .set_member_admin import SET_MEMBER_ADMIN_DEFAULTS
from .set_member_card import SET_MEMBER_CARD_DEFAULTS
from .set_member_title import SET_MEMBER_TITLE_DEFAULTS

# Register all default configurations
register_handle_defaults("kick_member", KICK_MEMBER_DEFAULTS)
register_handle_defaults("protect_member", PROTECT_MEMBER_DEFAULTS)
register_handle_defaults("block_member", BLOCK_MEMBER_DEFAULTS)
register_handle_defaults("chat", CHAT_DEFAULTS)
register_handle_defaults("member_mute", MEMBER_MUTE_DEFAULTS)
register_handle_defaults("recall_message", RECALL_MESSAGE_DEFAULTS)
register_handle_defaults("remote_mute", REMOTE_MUTE_DEFAULTS)
register_handle_defaults("remote_kick", REMOTE_KICK_DEFAULTS)
register_handle_defaults("remote_block", REMOTE_BLOCK_DEFAULTS)
register_handle_defaults("remote_announcement", REMOTE_ANNOUNCEMENT_DEFAULTS)
register_handle_defaults("mass_announcement", MASS_ANNOUNCEMENT_DEFAULTS)
register_handle_defaults(
    "restart_protocol_endpoint", RESTART_PROTOCOL_ENDPOINT_DEFAULTS
)
register_handle_defaults("send_announcement", SEND_ANNOUNCEMENT_DEFAULTS)
register_handle_defaults("set_member_card", SET_MEMBER_CARD_DEFAULTS)
register_handle_defaults("set_member_title", SET_MEMBER_TITLE_DEFAULTS)
register_handle_defaults("set_member_admin", SET_MEMBER_ADMIN_DEFAULTS)
register_handle_defaults("set_group_name", SET_GROUP_NAME_DEFAULTS)
register_handle_defaults("set_group_avatar", SET_GROUP_AVATAR_DEFAULTS)

__all__ = [
    "HANDLE_DEFAULTS_REGISTRY",
    "register_handle_defaults",
]
