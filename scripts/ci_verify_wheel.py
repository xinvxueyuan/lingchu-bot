#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""CI wheel contents verification.

Asserts the built wheel exposes the Lingchu Bot top-level packages. Exits
non-zero if any module is missing.

Usage:
    python scripts/ci_verify_wheel.py [dist_dir]

The default dist_dir is "dist/" (relative to the current working directory).
The script auto-discovers the first ``*.whl`` file under the directory.
"""

from __future__ import annotations

from pathlib import Path
import sys
from zipfile import ZipFile

# Modules that MUST appear inside the wheel. Keep in sync with the package
# layout under ``src/plugins/nonebot_plugin_lingchu_bot/`` and the helper
# package emitted by ``_lingchu_bot_contracts``.
EXPECTED_MODULES: tuple[str, ...] = (
    "_lingchu_bot_contracts",
    "nonebot_plugin_lingchu_bot",
)


def verify_wheel(dist_dir: Path) -> None:
    """Verify ``dist_dir`` contains a wheel that exposes ``EXPECTED_MODULES``."""
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"No wheel found under {dist_dir}")
    wheel = wheels[0]
    with ZipFile(wheel) as z:
        names = z.namelist()
    missing = [m for m in EXPECTED_MODULES if not any(n.startswith(m) for n in names)]
    if missing:
        raise SystemExit(f"Missing modules in {wheel.name}: {', '.join(missing)}")
    print(f"✓ All modules present in wheel: {', '.join(EXPECTED_MODULES)}")


def main(argv: list[str]) -> None:
    dist_dir = Path(argv[1]) if len(argv) > 1 else Path("dist")
    verify_wheel(dist_dir)


if __name__ == "__main__":
    main(sys.argv)
