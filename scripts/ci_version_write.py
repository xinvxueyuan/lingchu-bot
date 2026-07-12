#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Write a version string into core/config.py and package.json.

Updates the ``core_version`` field in the config module and the
``version`` field in ``package.json`` to the specified version.

Environment variables:
    VERSION: The version string to write.
    CONFIG_PATH: Path to the config.py file (relative to repo root).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re


def update_config_file(version: str, path: Path) -> None:
    """Replace the core_version field in a Python config file.

    Args:
        version: The version string to write.
        path: Path to the config.py file.

    Raises:
        RuntimeError: If exactly one core_version field is not found.
    """
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


def update_package_json(version: str, pkg_path: Path) -> None:
    """Update the version field in package.json.

    Args:
        version: The version string to write.
        pkg_path: Path to the package.json file.
    """
    data = json.loads(pkg_path.read_text(encoding="utf-8"))
    data["version"] = version
    pkg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote version {version} into {pkg_path}")


def main() -> None:
    """Write version into config.py and package.json."""
    version = os.environ["VERSION"]
    config_path = Path(os.environ["CONFIG_PATH"])

    update_config_file(version, config_path)
    update_package_json(version, Path("package.json"))


if __name__ == "__main__":
    main()
