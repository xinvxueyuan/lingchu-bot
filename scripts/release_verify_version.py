#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Verify release version is synchronized across package files.

Checks that the version in ``pyproject.toml``, ``package.json``, and
``core/config.py`` all match the expected version.

Environment variables:
    VERSION: The expected version string.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tomllib


def main() -> None:
    """Verify version consistency across all package files."""
    expected = os.environ["VERSION"]
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    config_text = Path(
        "src/plugins/nonebot_plugin_lingchu_bot/core/config.py"
    ).read_text(encoding="utf-8")
    match = re.search(r'core_version:\s*str\s*=\s*"([^"]+)"', config_text)
    actual = {
        "pyproject.toml": pyproject["project"]["version"],
        "package.json": package["version"],
        "core/config.py": match.group(1) if match else None,
    }
    bad = {path: value for path, value in actual.items() if value != expected}
    if bad:
        raise SystemExit(f"Version mismatch: expected {expected}, got {bad}")
    print(f"Version {expected} is synchronized.")


if __name__ == "__main__":
    main()
