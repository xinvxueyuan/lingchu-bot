#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Print the highest ``v*`` git tag using PEP 440 ordering.

``git tag --sort=-v:refname`` uses git's version sort, which ranks a
pre-release like ``v0.4.1.dev7`` above the stable ``v0.4.1`` because the
extra ``.dev7`` component is considered greater.  This breaks version
derivation after a stable release: the bump logic would keep treating the
stale dev tag as "latest" and produce a version that precheck correctly
rejects (e.g. ``0.4.1.dev8`` is not greater than ``v0.4.1``).

This script re-sorts tags with PEP 440 semantics (via ``packaging``), so the
highest tag is the true latest version.  Prints nothing when no ``v*`` tags
exist.
"""

from __future__ import annotations

import subprocess

from packaging.version import Version


def main() -> None:
    """Print the highest ``v[0-9]*`` tag per PEP 440, or nothing if none."""
    result = subprocess.run(
        ["git", "tag", "--list", "v[0-9]*"],
        capture_output=True,
        text=True,
        check=True,
    )
    tags = [t.strip() for t in result.stdout.strip().splitlines() if t.strip()]

    latest: tuple[Version, str] | None = None
    for tag in tags:
        try:
            ver = Version(tag.lstrip("v"))
        except Exception:  # pragma: no cover - malformed local tag
            continue
        if latest is None or ver > latest[0]:
            latest = (ver, tag)

    if latest is not None:
        print(latest[1])


if __name__ == "__main__":
    main()
