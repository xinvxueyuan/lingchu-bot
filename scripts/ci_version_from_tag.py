#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Restore version from a git tag into core/config.py.

Used by release builds to ensure the version in the config module
matches the git tag. The ``v`` prefix is stripped from the tag if
present.

Environment variables:
    VERSION: The version string (tag name, with or without ``v`` prefix).
    CONFIG_PATH: Path to the config.py file (relative to repo root).
"""

from __future__ import annotations

import os
from pathlib import Path
import re


def main() -> None:
    """Restore version from tag into config.py."""
    version = os.environ["VERSION"]
    path = Path(os.environ["CONFIG_PATH"])

    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'core_version:\s*str\s*=\s*"[^"]*"',
        f'core_version: str = "{version}"',
        text,
        count=1,
    )

    if count != 1:
        raise RuntimeError("未找到唯一的 core_version 字段")

    path.write_text(new_text, encoding="utf-8")
    print(f"Restored version {version} into {path}")


if __name__ == "__main__":
    main()
