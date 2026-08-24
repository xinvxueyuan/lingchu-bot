"""Content integrity checksums for persisted TOML files.

A checksum line is appended after the TOML body so the file remains valid
TOML (the line is a comment) while still detecting corruption or tampering
on read. Files written before this feature simply have no checksum line and
are accepted as-is for forward compatibility.
"""

from __future__ import annotations

import hashlib

_CHECKSUM_PREFIX = "# lingchu-checksum: "


def compute_checksum(body: str) -> str:
    """Return the SHA-256 hex digest of a TOML body (without checksum line)."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def append_checksum(content: str) -> str:
    """Append a checksum line to TOML content."""
    body = content.rstrip()
    return f"{body}\n{_CHECKSUM_PREFIX}{compute_checksum(body)}\n"


def extract_checksum(content: str) -> tuple[str, str | None]:
    """Split content into (body_without_checksum_line, stored_checksum).

    Returns ``None`` for the checksum when the file carries no checksum line
    (legacy format), which callers treat as "not verifiable, accept".
    """
    stripped = content.rstrip("\n")
    lines = stripped.splitlines()
    if not lines:
        return content, None
    last = lines[-1]
    if last.startswith(_CHECKSUM_PREFIX):
        body = "\n".join(lines[:-1])
        return body, last[len(_CHECKSUM_PREFIX) :].strip()
    return content, None


def verify_checksum(content: str) -> bool:
    """Return True when the content is intact or carries no checksum line."""
    body, stored = extract_checksum(content)
    if stored is None:
        return True
    return compute_checksum(body) == stored
