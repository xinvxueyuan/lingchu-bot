"""WebUI 会话：HMAC 签名的无状态 Cookie。

改造后的 WebUI 由 NoneBot 同进程托管，不再有 Node 侧 JWT + 内存口令缓存两层状态。
会话收敛为**单个签名 Cookie**：

- 载荷只含过期时间与随机 nonce，不含任何用户数据；
- 签名密钥由"配置口令 + 进程启动 nonce"派生 —— 进程重启后密钥变化，
  所有既有会话自动失效（等价旧实现里 `session_expired` 的语义），
  无需进程内缓存、也无需清理过期条目；
- Cookie 收窄到 WebUI 子树（`Path={base}`），不会泄露到 NoneBot 其它路由。

本模块不依赖驱动器，可在不启动 NoneBot 的情况下导入与测试。
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import hmac
import secrets
import time

# Cookie 名：固定值，与前端无耦合（前端不读它，只依赖浏览器自动携带）。
WEBUI_SESSION_COOKIE: str = "lingchu_webui_session"

# 会话默认有效期（秒）：12 小时。
DEFAULT_SESSION_TTL_SECONDS: int = 12 * 60 * 60

# 会话主体：单用户系统，用户名锁定 root。
SESSION_SUBJECT: str = "root"

# 进程启动 nonce：模块导入时生成一次。重启进程即轮换签名密钥。
_PROCESS_NONCE: bytes = secrets.token_bytes(32)

# 签名域分隔符：拼在口令与 nonce 之间，避免不同长度口令产生相同拼接串。
_KEY_LABEL: bytes = b"lingchu-webui-session\0"


@dataclass(frozen=True, slots=True)
class SessionClaims:
    """已校验的会话载荷。

    Attributes:
        sub: 会话主体（固定 `root`）。
        expires_at: 过期时间（Unix 秒）。

    """

    sub: str
    expires_at: int


class SessionDisabledError(RuntimeError):
    """未配置 `LINGCHU_WEBUI_PASSWORD`，登录一律拒绝（fail-closed）。"""


def _signing_key(password: str) -> bytes:
    """由登录口令与进程 nonce 派生签名密钥。

    Args:
        password: `LINGCHU_WEBUI_PASSWORD` 配置值（非空）。

    Returns:
        bytes: 32 字节 HMAC 密钥。

    """
    material = _KEY_LABEL + password.encode() + b"|" + _PROCESS_NONCE
    return hashlib.sha256(material).digest()


def _encode_payload(expires_at: int) -> str:
    """把过期时间与随机 nonce 编码为 base64url 文本。

    Args:
        expires_at: 过期时间（Unix 秒）。

    Returns:
        str: `base64url(exp.nonce)`。

    """
    nonce = secrets.token_urlsafe(12)
    raw = f"{expires_at}.{nonce}".encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _decode_payload(payload: str) -> tuple[int, str] | None:
    """解码 base64url 载荷。

    Args:
        payload: `base64url(exp.nonce)` 文本。

    Returns:
        tuple[int, str] | None: `(expires_at, nonce)`；格式非法时返回 None。

    """
    padded = payload + "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    expires_text, separator, nonce = raw.partition(".")
    if not separator or not nonce or not expires_text.isdigit():
        return None
    return int(expires_text), nonce


def issue_session(
    password: str,
    *,
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    now: float | None = None,
) -> tuple[str, int]:
    """签发一个新的会话 Cookie 值。

    Args:
        password: 登录口令；空字符串表示未启用 WebUI，此时拒绝签发。
        ttl_seconds: 有效期（秒），非正值回退为默认值。
        now: 当前时间戳（测试注入用），缺省取系统时间。

    Returns:
        tuple[str, int]: `(cookie_value, expires_at)`。

    Raises:
        SessionDisabledError: `password` 为空（fail-closed）。

    """
    if not password:
        raise SessionDisabledError
    ttl = ttl_seconds if ttl_seconds > 0 else DEFAULT_SESSION_TTL_SECONDS
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + ttl
    payload = _encode_payload(expires_at)
    signature = hmac.new(
        _signing_key(password), payload.encode(), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{payload}.{encoded_signature}", expires_at


def _split_and_check_signature(password: str, token: str | None) -> int | None:
    """校验 token 结构与签名，返回载荷中的过期时间。

    拆成独立函数而非在 `verify_session` 里连续早返回：签名校验的每一步
    失败都是"无效会话"，但把它们压进一个布尔式会掩盖具体失败点，
    也不便于将来按失败原因记录审计日志。

    Args:
        password: 登录口令（非空）。
        token: Cookie 值。

    Returns:
        int | None: 签名有效时返回过期时间；否则 None。

    """
    if not token:
        return None
    payload, separator, signature_text = token.rpartition(".")
    if not separator or not payload or not signature_text:
        return None
    decoded = _decode_payload(payload)
    if decoded is None:
        return None

    padded = signature_text + "=" * (-len(signature_text) % 4)
    try:
        provided = base64.urlsafe_b64decode(padded.encode())
    except (binascii.Error, ValueError):
        return None
    expected = hmac.new(
        _signing_key(password), payload.encode(), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(provided, expected):
        return None
    return decoded[0]


def verify_session(
    password: str,
    token: str | None,
    *,
    now: float | None = None,
) -> SessionClaims | None:
    """校验会话 Cookie 值。

    校验签名（恒定时间比较）、过期时间与载荷格式。任何一步失败都返回
    `None`，调用方据此返回 401。

    Args:
        password: 登录口令；空字符串时一切会话无效。
        token: Cookie 值。
        now: 当前时间戳（测试注入用），缺省取系统时间。

    Returns:
        SessionClaims | None: 合法时返回载荷，否则 None。

    """
    if not password:
        return None
    expires_at = _split_and_check_signature(password, token)
    if expires_at is None:
        return None
    current = time.time() if now is None else now
    if expires_at <= current:
        return None
    return SessionClaims(sub=SESSION_SUBJECT, expires_at=expires_at)
