from typing import Any

from arclet.alconna import Alconna, Args
from nonebot.adapters import Bot, Event
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import on_alconna

from ....repositories import permissions as repository
from ....services.permissions import (
    add_group_member,
    bind_command_key,
    ensure_default_permission_state,
    grant_group_to_node,
    is_superuser,
    list_tree_lines,
)
from .command_triggers import COMMAND_TRIGGERS
from .common import selected_adapter_handle

_PERMISSION = COMMAND_TRIGGERS["permission"]

permission_cmd: type[Matcher] = on_alconna(
    command=Alconna(
        _PERMISSION.primary,
        Args["action?", str, "help"]["arg1?", str, ""]["arg2?", str, ""][
            "arg3?", str, ""
        ]["arg4?", str, ""]["arg5?", str, ""],
    ),
    aliases=_PERMISSION.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(permission_cmd, "permission")


@selected_adapter_handle(permission_cmd, "~onebot.v11")
async def onebot11_permission(  # noqa: PLR0913
    bot: Bot,
    event: Event,
    action: str = "help",
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
) -> Any:
    return await _handle_permission(bot, event, action, arg1, arg2, arg3, arg4, arg5)


@selected_adapter_handle(permission_cmd, "~milky")
async def milky_permission(  # noqa: PLR0913
    bot: Bot,
    event: Event,
    action: str = "help",
    arg1: str = "",
    arg2: str = "",
    arg3: str = "",
    arg4: str = "",
    arg5: str = "",
) -> Any:
    return await _handle_permission(bot, event, action, arg1, arg2, arg3, arg4, arg5)


async def _handle_permission(  # noqa: PLR0911, PLR0913
    bot: Bot,
    event: Event,
    action: str,
    arg1: str,
    arg2: str,
    arg3: str,
    arg4: str,
    arg5: str,
) -> Any:
    _ = bot
    user_id = _event_user_id(event)
    if not is_superuser(user_id):
        return await permission_cmd.finish(message="权限不足: 仅 superusers 可管理权限")

    normalized = action.casefold()
    if normalized in {"sync", "同步"}:
        await ensure_default_permission_state(force=True)
        return await permission_cmd.finish(message="权限树已同步")

    if normalized in {"tree", "list", "树", "列表"}:
        return await _finish_permission_tree(arg1)

    if normalized in {"grant", "授权"}:
        if not arg1 or not arg2:
            return await permission_cmd.finish(
                message=(
                    "用法: 权限 grant <group_key> <node_path> "
                    "[resource_type] [resource_id]"
                )
            )
        ok = await grant_group_to_node(
            group_key=arg1,
            node_path=arg2,
            resource_type=arg3 or None,
            resource_id=arg4 or None,
        )
        message = "授权已写入" if ok else "授权失败: 组或权限节点不存在"
        return await permission_cmd.finish(message=message)

    if normalized in {"member", "add-member", "成员"}:
        if not arg1 or not arg2 or not arg3:
            return await permission_cmd.finish(
                message=(
                    "用法: 权限 member <group_key> <platform_id> <user_id> "
                    "[resource_type] [resource_id]"
                )
            )
        ok = await add_group_member(
            group_key=arg1,
            platform_id=arg2,
            user_id=arg3,
            resource_type=arg4 or None,
            resource_id=arg5 or None,
        )
        message = "成员已写入" if ok else "成员写入失败: 组不存在"
        return await permission_cmd.finish(message=message)

    if normalized in {"native-on", "native-off"}:
        return await _finish_native_mapping(normalized, arg1)

    return await permission_cmd.finish(
        message=(
            "权限命令:\n"
            "- 权限 sync\n"
            "- 权限 tree [数量]\n"
            "- 权限 grant <group_key> <node_path> [resource_type] [resource_id]\n"
            "- 权限 member <group_key> <platform_id> <user_id> "
            "[resource_type] [resource_id]\n"
            "- 权限 native-on|native-off <owner|admin>"
        )
    )


async def _finish_native_mapping(action: str, native_role_text: str) -> Any:
    if not native_role_text:
        return await permission_cmd.finish(
            message="用法: 权限 native-on|native-off <owner|admin>"
        )
    native_role = native_role_text.casefold()
    if native_role not in {"owner", "admin"}:
        return await permission_cmd.finish(message="无效的角色: 仅支持 owner 或 admin")
    updated_count, _ = await repository.set_native_role_mapping_enabled(
        platform_id="qq",
        adapter_id=None,
        resource_type="group",
        native_role=native_role,
        is_enabled=action == "native-on",
    )
    if updated_count == 0:
        return await permission_cmd.finish(
            message=f"原生身份映射未找到，请先执行 权限 sync: {native_role}"
        )
    state = "启用" if action == "native-on" else "禁用"
    return await permission_cmd.finish(message=f"原生身份映射已{state}: {native_role}")


def _event_user_id(event: Event) -> str | None:
    try:
        return str(event.get_user_id())
    except Exception:  # noqa: BLE001
        value = getattr(event, "user_id", None)
        return None if value is None else str(value)


async def _finish_permission_tree(limit_text: str) -> Any:
    limit = _parse_positive_limit(limit_text)
    if limit is None and limit_text:
        return await permission_cmd.finish(
            message="无效的数量参数: 请使用正整数，例如: 权限 tree 200"
        )
    lines = await list_tree_lines(limit=limit or 80)
    return await permission_cmd.finish(message="\n".join(["权限树", *lines]))


def _parse_positive_limit(value: str) -> int | None:
    if not value:
        return None
    try:
        limit = int(value)
    except ValueError:
        return None
    return limit if limit > 0 else None


async def import_handle() -> Any:
    return None
