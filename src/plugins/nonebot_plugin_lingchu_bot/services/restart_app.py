"""Application restart service with user confirmation and startup notification."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sys
from time import monotonic
from typing import Any, Final

from nonebot import get_bot, get_bots, logger, on_message, require
from nonebot.adapters import Bot, Event
from nonebot.rule import Rule

from ..i18n import _async as _
from ..platforms import get_platform_profile, resolve_adapter_id

RESTART_CONFIRM_TTL_SECONDS: Final[float] = 60.0
CONFIRM_WORDS: frozenset[str] = frozenset({"是", "确认", "确定", "yes", "y"})
CANCEL_WORDS: frozenset[str] = frozenset({"否", "取消", "no", "n"})
LC_HOSTED_ENV = "LINGCHU_LC_HOSTED"
RESTART_FLAG_PATH_ENV = "LINGCHU_RESTART_FLAG_PATH"
RESTART_BY_ENV = "LINGCHU_RESTART_BY"

_ONEBOT11_ADAPTER_ID: Final[str] = "~onebot.v11"
_TELEGRAM_ADAPTER_ID: Final[str] = "~telegram"
_QQ_PLATFORM_ID: Final[str] = "qq"
_TELEGRAM_PLATFORM_ID: Final[str] = "telegram"
_RESTART_WORKER_SRC: Final[Path] = (
    Path(__file__).resolve().parent.parent / "restart_worker.py"
)


@dataclass(frozen=True, slots=True)
class PendingRestartApp:
    """A restart request awaiting user confirmation."""

    platform_id: str
    adapter_id: str
    bot_id: str
    conversation_type: str
    conversation_id: str
    account_id: str
    created_at: float


_pending_restart_app: dict[tuple[str, str, str], PendingRestartApp] = {}
_ttl_tasks: dict[tuple[str, str, str], asyncio.Task[None]] = {}
_spawned_scripts: set[asyncio.subprocess.Process] = set()


def register_pending_restart_app(
    *,
    platform_id: str,
    adapter_id: str,
    bot_id: str,
    conversation_type: str,
    conversation_id: str,
    account_id: str,
) -> None:
    """Register a pending restart request and arm its confirmation TTL."""
    key = (platform_id, conversation_id, account_id)
    pending = PendingRestartApp(
        platform_id=platform_id,
        adapter_id=adapter_id,
        bot_id=bot_id,
        conversation_type=conversation_type,
        conversation_id=conversation_id,
        account_id=account_id,
        created_at=monotonic(),
    )
    _pending_restart_app[key] = pending
    _ttl_tasks[key] = asyncio.create_task(
        _ttl_timeout(key, pending), name="restart_app:confirm_ttl"
    )


def clear_pending_restart_app() -> None:
    """Clear every pending restart request and cancel its TTL task."""
    for task in _ttl_tasks.values():
        task.cancel()
    _ttl_tasks.clear()
    _pending_restart_app.clear()


def clear_pending_restart_app_for(
    *,
    platform_id: str,
    conversation_id: str,
    account_id: str,
) -> bool:
    """Pop the pending restart request for a conversation and cancel its TTL."""
    key = (platform_id, conversation_id, account_id)
    task = _ttl_tasks.pop(key, None)
    if task is not None:
        task.cancel()
    return _pending_restart_app.pop(key, None) is not None


def list_pending_restart_app() -> tuple[PendingRestartApp, ...]:
    """Return all pending restart requests."""
    return tuple(_pending_restart_app.values())


async def notify_restart_success(platform_id: str, account_id: str) -> bool:
    """Notify the requesting account that the application restarted."""
    message = await _("灵初已成功重启")
    for bot in get_bots().values():
        if _extract_bot_platform(bot) != platform_id:
            continue
        try:
            if platform_id == _QQ_PLATFORM_ID:
                await bot.send_private_msg(user_id=int(account_id), message=message)
            elif platform_id == _TELEGRAM_PLATFORM_ID:
                await bot.send_message(chat_id=int(account_id), text=message)
            else:
                continue
        except Exception:
            logger.exception("Failed to send restart success notification")
            continue
        return True
    return False


def _extract_bot_platform(bot: Any) -> str | None:
    """Resolve a bot instance to its Lingchu platform id."""
    adapter = getattr(bot, "adapter", None)
    get_name = getattr(adapter, "get_name", None)
    if get_name is None:
        return None
    try:
        adapter_name = str(get_name())
    except (AttributeError, TypeError, ValueError):
        return None
    adapter_id = resolve_adapter_id(adapter_name)
    if adapter_id is None:
        return None
    profile = get_platform_profile(adapter_id)
    if profile is None:
        return None
    return profile.platform_id


def _has_pending_restart_app(bot: Bot, event: Event) -> bool:
    """Rule: the message arrives in a conversation with a pending restart."""
    context = _extract_context(bot, event)
    if context is None:
        return False
    platform_id, _conversation_type, conversation_id, account_id = context
    return (platform_id, conversation_id, account_id) in _pending_restart_app


_restart_app_confirm_matcher = on_message(
    rule=Rule(_has_pending_restart_app), priority=10, block=False
)


@_restart_app_confirm_matcher.handle()
async def _handle_restart_app_confirm(bot: Bot, event: Event) -> None:
    """Confirm or cancel a pending application restart from the follow-up."""
    context = _extract_context(bot, event)
    if context is None:
        return
    platform_id, _conversation_type, conversation_id, account_id = context
    key = (platform_id, conversation_id, account_id)
    pending = _pending_restart_app.get(key)
    if pending is None:
        return
    text = event.get_plaintext().strip().lower()
    if text in CONFIRM_WORDS:
        _cancel_ttl(key)
        _pending_restart_app.pop(key, None)
        await _restart_app_confirm_matcher.send(await _("正在重启应用，请稍候..."))
        await execute_restart_app(pending)
    elif text in CANCEL_WORDS:
        _cancel_ttl(key)
        _pending_restart_app.pop(key, None)
        await _restart_app_confirm_matcher.send(await _("已取消重启"))


def _extract_context(bot: Any, event: Any) -> tuple[str, str, str, str] | None:
    """Extract (platform_id, conversation_type, conversation_id, account_id)."""
    adapter = getattr(bot, "adapter", None)
    get_name = getattr(adapter, "get_name", None)
    if get_name is None:
        return None
    try:
        adapter_name = str(get_name())
    except (AttributeError, TypeError, ValueError):
        return None
    adapter_id = resolve_adapter_id(adapter_name)
    if adapter_id is None:
        return None
    profile = get_platform_profile(adapter_id)
    if profile is None:
        return None
    platform_id = profile.platform_id

    if adapter_id == _ONEBOT11_ADAPTER_ID:
        from nonebot.adapters.onebot.v11.event import (
            GroupMessageEvent as OneBot11GroupMessageEvent,
            PrivateMessageEvent as OneBot11PrivateMessageEvent,
        )

        if isinstance(event, OneBot11PrivateMessageEvent):
            return (platform_id, "private", str(event.user_id), str(event.user_id))
        if isinstance(event, OneBot11GroupMessageEvent):
            return (platform_id, "group", str(event.group_id), str(event.user_id))
        return None
    if adapter_id == _TELEGRAM_ADAPTER_ID:
        from nonebot.adapters.telegram.event import (
            GroupMessageEvent as TelegramGroupMessageEvent,
            PrivateMessageEvent as TelegramPrivateMessageEvent,
        )

        if isinstance(event, TelegramPrivateMessageEvent):
            return (platform_id, "private", str(event.chat.id), str(event.from_.id))
        if isinstance(event, TelegramGroupMessageEvent):
            return (platform_id, "group", str(event.chat.id), str(event.from_.id))
        return None
    return None


async def _ttl_timeout(key: tuple[str, str, str], pending: PendingRestartApp) -> None:
    """Cancel a pending restart request when its confirmation window lapses."""
    await asyncio.sleep(RESTART_CONFIRM_TTL_SECONDS)
    if _pending_restart_app.get(key) is not pending:
        return
    _pending_restart_app.pop(key, None)
    _ttl_tasks.pop(key, None)
    bot = _get_bot(pending.bot_id)
    await _send_to_conversation(bot, pending, await _("重启已超时取消"))


def _get_bot(bot_id: str) -> Bot | None:
    try:
        return get_bot(bot_id)
    except ValueError:
        return None


async def _send_to_conversation(
    bot: Bot | None, pending: PendingRestartApp, message: str
) -> None:
    """Send a message back to the conversation that requested the restart."""
    if bot is None:
        return
    try:
        if pending.platform_id == _QQ_PLATFORM_ID:
            if pending.conversation_type == "private":
                await bot.send_private_msg(
                    user_id=int(pending.account_id), message=message
                )
            else:
                await bot.send_group_msg(
                    group_id=int(pending.conversation_id), message=message
                )
        elif pending.platform_id == _TELEGRAM_PLATFORM_ID:
            chat_id = int(
                pending.account_id
                if pending.conversation_type == "private"
                else pending.conversation_id
            )
            await bot.send_message(chat_id=chat_id, text=message)
    except Exception:
        logger.exception("Failed to send restart confirmation timeout message")


async def execute_restart_app(pending: PendingRestartApp) -> None:
    """Execute the confirmed restart through the hosted flag or local script."""
    if os.environ.get(LC_HOSTED_ENV) == "1":
        await _write_restart_flag(pending)
    else:
        await _spawn_restart_script(pending)


async def _write_restart_flag(pending: PendingRestartApp) -> None:
    """Atomically write the hosted restart request flag file."""
    flag_path = os.environ.get(RESTART_FLAG_PATH_ENV)
    if not flag_path:
        logger.error(
            "{} is not set; cannot request a hosted restart", RESTART_FLAG_PATH_ENV
        )
        return
    path = Path(flag_path)
    payload = json.dumps(
        {"platform": pending.platform_id, "account_id": pending.account_id},
        ensure_ascii=False,
    )
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(path)
    except OSError:
        logger.exception("Failed to write restart flag file")


async def _spawn_restart_script(pending: PendingRestartApp) -> None:
    """Copy and spawn the self-contained restart worker script."""
    require("nonebot_plugin_localstore")
    from nonebot_plugin_localstore import get_plugin_cache_dir

    cache_dir = get_plugin_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    script_dst = cache_dir / "restart_worker.py"
    try:
        shutil.copy2(_RESTART_WORKER_SRC, script_dst)
    except OSError:
        logger.exception("Failed to copy restart worker script")
        return
    env = dict(os.environ)
    env[RESTART_BY_ENV] = f"{pending.platform_id}:{pending.account_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_dst),
            str(os.getpid()),
            str(Path.cwd()),
            env=env,
            start_new_session=True,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError:
        logger.exception("Failed to spawn restart worker script")
        return
    _spawned_scripts.add(proc)


def _cancel_ttl(key: tuple[str, str, str]) -> None:
    task = _ttl_tasks.pop(key, None)
    if task is not None:
        task.cancel()
