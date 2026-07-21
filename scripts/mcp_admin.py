"""Administrative CLI for inbound MCP principals and exact grants."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
from typing import Any, cast


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Lingchu inbound MCP authorization records.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    principal = commands.add_parser("principal-create")
    principal.add_argument("--principal-id", required=True)
    principal.add_argument("--issuer", required=True)
    principal.add_argument(
        "--identity-kind",
        choices=("subject", "client_id"),
        default="subject",
    )
    principal.add_argument("--identity-value", required=True)
    principal.add_argument("--display-name", required=True)

    for name, enabled in (
        ("principal-enable", True),
        ("principal-disable", False),
    ):
        command = commands.add_parser(name)
        command.add_argument("--principal-id", required=True)
        command.set_defaults(enabled=enabled)

    grant = commands.add_parser("grant-create")
    grant.add_argument("--grant-id", required=True)
    grant.add_argument("--principal-id", required=True)
    grant.add_argument("--platform", required=True)
    grant.add_argument("--adapter", required=True)
    grant.add_argument("--protocol", required=True)
    grant.add_argument("--bot-id", required=True)
    grant.add_argument(
        "--conversation-type",
        choices=("group", "private"),
        required=True,
    )
    grant.add_argument("--conversation-id", required=True)

    revoke = commands.add_parser("grant-revoke")
    revoke.add_argument("--grant-id", required=True)

    grants = commands.add_parser("grant-list")
    grants.add_argument("--principal-id", required=True)
    return parser


def _json_default(value: object) -> object:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def _print(value: object) -> None:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(cast("Any", value))
    elif isinstance(value, tuple):
        value = [asdict(cast("Any", item)) for item in value]
    print(json.dumps(value, default=_json_default, ensure_ascii=False, sort_keys=True))


async def _run(args: argparse.Namespace) -> None:
    from nonebot_plugin_orm import get_session, init_orm

    from nonebot_plugin_lingchu_bot.repositories import (
        mcp_authorization,
    )
    from nonebot_plugin_lingchu_bot.services.mcp_server.administration import (
        CreateResourceGrantRequest,
        CreateServicePrincipalRequest,
        OAuthIdentityKind,
    )
    from nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
        BotAddress,
        ConversationAddress,
    )

    await init_orm()
    async with get_session() as session:
        if args.command == "principal-create":
            result = await mcp_authorization.create_service_principal(
                session,
                CreateServicePrincipalRequest(
                    args.principal_id,
                    args.issuer,
                    OAuthIdentityKind(args.identity_kind),
                    args.identity_value,
                    args.display_name,
                ),
            )
        elif args.command in {"principal-enable", "principal-disable"}:
            result = await mcp_authorization.set_service_principal_enabled(
                session,
                args.principal_id,
                enabled=args.enabled,
            )
        elif args.command == "grant-create":
            result = await mcp_authorization.create_resource_grant(
                session,
                CreateResourceGrantRequest(
                    args.grant_id,
                    args.principal_id,
                    BotAddress(
                        args.platform,
                        args.adapter,
                        args.protocol,
                        args.bot_id,
                    ),
                    ConversationAddress(
                        args.conversation_type,
                        args.conversation_id,
                    ),
                ),
            )
        elif args.command == "grant-revoke":
            result = await mcp_authorization.revoke_resource_grant(
                session,
                args.grant_id,
            )
        else:
            result = await mcp_authorization.list_active_resource_grants(
                session,
                principal_id=args.principal_id,
            )
        if args.command != "grant-list":
            await session.commit()
    _print(result)


def main() -> None:
    """Initialize NoneBot plugins and execute one administrative transaction."""
    args = _parser().parse_args()
    import nonebot

    nonebot.init()
    from nonebot.adapters.onebot.v11 import Adapter

    nonebot.get_driver().register_adapter(Adapter)
    if nonebot.load_plugin("nonebot_plugin_orm") is None:
        raise RuntimeError("failed to load nonebot-plugin-orm")
    if nonebot.load_plugin("nonebot_plugin_lingchu_bot") is None:
        raise RuntimeError("failed to load lingchu-bot")
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
