"""Handle configuration defaults registry.

This module provides a centralized registry for default configurations
of different handle commands. Each handle registers its pydantic model
class using the `register_handle_defaults` function. The model class
serves as both the default-value source (via `model_cls().model_dump()`)
and the validation schema (via `type_validate_python(model_cls, data)`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

HANDLE_DEFAULTS_REGISTRY: dict[str, type[BaseModel]] = {}


def register_handle_defaults(command_key: str, model_cls: type[BaseModel]) -> None:
    """Register a pydantic model class as the default handle configuration.

    Args:
        command_key: The unique identifier for the handle command.
        model_cls: A pydantic ``BaseModel`` subclass declaring the handle's
            ``enabled``, ``defaults``, and ``policies`` fields. The model's
            field defaults are used as the configuration fallback values,
            and the model itself is used to validate TOML content via
            ``type_validate_python``.

    Raises:
        ValueError: If command_key is already registered.
    """
    if command_key in HANDLE_DEFAULTS_REGISTRY:
        raise ValueError(f"duplicate key: {command_key}")
    HANDLE_DEFAULTS_REGISTRY[command_key] = model_cls


# Import and register default configurations
from .block_member import BlockMemberConfig
from .kick_member import KickMemberConfig
from .mass_announcement import MassAnnouncementConfig
from .member_mute import MemberMuteConfig
from .protect_member import ProtectMemberConfig
from .recall_message import RecallMessageConfig
from .remote_announcement import RemoteAnnouncementConfig
from .remote_block import RemoteBlockConfig
from .remote_kick import RemoteKickConfig
from .remote_mute import RemoteMuteConfig
from .restart_protocol_endpoint import RestartProtocolEndpointConfig
from .send_announcement import SendAnnouncementConfig
from .set_group_avatar import SetGroupAvatarConfig
from .set_group_name import SetGroupNameConfig
from .set_member_admin import SetMemberAdminConfig
from .set_member_card import SetMemberCardConfig
from .set_member_title import SetMemberTitleConfig

# Register all default configurations
register_handle_defaults("kick_member", KickMemberConfig)
register_handle_defaults("protect_member", ProtectMemberConfig)
register_handle_defaults("block_member", BlockMemberConfig)
register_handle_defaults("member_mute", MemberMuteConfig)
register_handle_defaults("recall_message", RecallMessageConfig)
register_handle_defaults("remote_mute", RemoteMuteConfig)
register_handle_defaults("remote_kick", RemoteKickConfig)
register_handle_defaults("remote_block", RemoteBlockConfig)
register_handle_defaults("remote_announcement", RemoteAnnouncementConfig)
register_handle_defaults("mass_announcement", MassAnnouncementConfig)
register_handle_defaults("restart_protocol_endpoint", RestartProtocolEndpointConfig)
register_handle_defaults("send_announcement", SendAnnouncementConfig)
register_handle_defaults("set_member_card", SetMemberCardConfig)
register_handle_defaults("set_member_title", SetMemberTitleConfig)
register_handle_defaults("set_member_admin", SetMemberAdminConfig)
register_handle_defaults("set_group_name", SetGroupNameConfig)
register_handle_defaults("set_group_avatar", SetGroupAvatarConfig)

__all__ = [
    "HANDLE_DEFAULTS_REGISTRY",
    "register_handle_defaults",
]
