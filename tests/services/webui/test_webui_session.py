"""`core/webui_session.py` 的单元测试：无状态签名会话的签发与校验。

覆盖点：
- 未配置口令 fail-closed（`SessionDisabledError` / 校验一律 None）；
- 签发后可解出 `sub='root'` 与 `expires_at`；
- 篡改载荷、篡改签名、截断、空 token 一律无效；
- 过期边界（`expires_at <= now` 即失效）；
- 换口令后旧 token 失效、非正 ttl 回退默认值、两次签发互不相同。
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.webui_session import (
    DEFAULT_SESSION_TTL_SECONDS,
    SESSION_SUBJECT,
    WEBUI_SESSION_COOKIE,
    SessionDisabledError,
    issue_session,
    verify_session,
)

_PASSWORD = "correct horse battery staple"
_NOW = 1_000.0


def test_cookie_name_and_subject_constants() -> None:
    assert WEBUI_SESSION_COOKIE == "lingchu_webui_session"
    assert SESSION_SUBJECT == "root"
    assert DEFAULT_SESSION_TTL_SECONDS == 43_200


def test_issue_rejects_empty_password() -> None:
    with pytest.raises(SessionDisabledError):
        issue_session("", now=_NOW)


def test_issue_and_verify_roundtrip() -> None:
    token, expires_at = issue_session(_PASSWORD, ttl_seconds=60, now=_NOW)
    assert expires_at == int(_NOW) + 60
    claims = verify_session(_PASSWORD, token, now=_NOW)
    assert claims is not None
    assert claims.sub == "root"
    assert claims.expires_at == expires_at


def test_verify_rejects_everything_when_password_empty() -> None:
    token, _ = issue_session(_PASSWORD, now=_NOW)
    assert verify_session("", token, now=_NOW) is None


@pytest.mark.parametrize("token", [None, "", "   "])
def test_verify_rejects_missing_token(token: str | None) -> None:
    assert verify_session(_PASSWORD, token, now=_NOW) is None


def test_verify_rejects_tampered_payload() -> None:
    token, _ = issue_session(_PASSWORD, ttl_seconds=60, now=_NOW)
    payload, _, signature = token.rpartition(".")
    # 换一个载荷（延长有效期）但保留原签名。
    forged_payload, _ = issue_session(_PASSWORD, ttl_seconds=99_999, now=_NOW)
    forged = f"{forged_payload.rpartition('.')[0]}.{signature}"
    assert forged_payload != payload
    assert verify_session(_PASSWORD, forged, now=_NOW) is None


def test_verify_rejects_tampered_signature() -> None:
    token, _ = issue_session(_PASSWORD, ttl_seconds=60, now=_NOW)
    payload, _, signature = token.rpartition(".")
    flipped = ("A" if signature[:1] != "A" else "B") + signature[1:]
    assert verify_session(_PASSWORD, f"{payload}.{flipped}", now=_NOW) is None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda token: token[:-4],  # 截断尾部（签名残缺）
        lambda token: token[: len(token) // 2],  # 截断到只剩载荷片段
        lambda token: token.rpartition(".")[0],  # 丢掉签名分隔符
        lambda token: f".{token}",  # 空载荷
        lambda token: f"{token}.",  # 空签名
        lambda token: f"!!!.{token.rpartition('.')[2]}",  # 载荷不是合法 base64url
    ],
)
def test_verify_rejects_malformed_tokens(mutator: Callable[[str], str]) -> None:
    token, _ = issue_session(_PASSWORD, ttl_seconds=60, now=_NOW)
    assert verify_session(_PASSWORD, mutator(token), now=_NOW) is None


def test_verify_boundary_expiry() -> None:
    token, _ = issue_session(_PASSWORD, ttl_seconds=10, now=_NOW)
    assert verify_session(_PASSWORD, token, now=1_009) is not None
    assert verify_session(_PASSWORD, token, now=1_010) is None
    assert verify_session(_PASSWORD, token, now=1_011) is None


def test_verify_rejects_after_password_change() -> None:
    token, _ = issue_session(_PASSWORD, ttl_seconds=60, now=_NOW)
    assert verify_session("another password", token, now=_NOW) is None


@pytest.mark.parametrize("ttl", [0, -1, -60])
def test_non_positive_ttl_falls_back_to_default(ttl: int) -> None:
    _, expires_at = issue_session(_PASSWORD, ttl_seconds=ttl, now=_NOW)
    assert expires_at == int(_NOW) + DEFAULT_SESSION_TTL_SECONDS


def test_two_issues_differ_due_to_nonce() -> None:
    first, first_expires = issue_session(_PASSWORD, ttl_seconds=60, now=_NOW)
    second, second_expires = issue_session(_PASSWORD, ttl_seconds=60, now=_NOW)
    assert first != second
    assert first_expires == second_expires
    assert verify_session(_PASSWORD, first, now=_NOW) is not None
    assert verify_session(_PASSWORD, second, now=_NOW) is not None
