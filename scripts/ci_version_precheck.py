#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pre-bump validation for CI version pipeline.

Verifies that a new version is valid PEP 440, greater than all existing
git tags, consistent across source files (advisory), and not already
tagged.

Environment variables:
    NEW_VERSION: The candidate version string to validate.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

from packaging.version import Version


def main() -> None:
    """Run all pre-bump version checks."""
    new_version = os.environ["NEW_VERSION"]

    # 1. Validate PEP 440
    try:
        v = Version(new_version)
        print(f"  {new_version} is valid PEP 440")
    except Exception as e:
        raise SystemExit(f"  {new_version} is not valid PEP 440: {e}") from e

    # 2. Must be greater than ALL existing tags
    result = subprocess.run(
        ["git", "tag", "--list", "v[0-9]*"],
        capture_output=True,
        text=True,
        check=True,
    )
    tags = [t.strip() for t in result.stdout.strip().splitlines() if t.strip()]
    for tag in tags:
        tag_ver = Version(tag.lstrip("v"))
        if not v > tag_ver:
            raise SystemExit(
                f"  {new_version} is not greater than existing tag {tag} ({tag_ver})"
            )
    print(f"  {new_version} is greater than all {len(tags)} existing tags")

    # 3. Source files consistency check (advisory)
    try:
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]["version"]
        package = json.loads(Path("package.json").read_text(encoding="utf-8"))[
            "version"
        ]
        config_match = re.search(
            r'core_version:\s*str\s*=\s*"([^"]+)"',
            Path("src/plugins/nonebot_plugin_lingchu_bot/core/config.py").read_text(
                encoding="utf-8"
            ),
        )
        config_ver = config_match.group(1) if config_match else None
        if pyproject == package == config_ver:
            print(f"  Source files are consistent at {pyproject}")
        else:
            print(
                f"  Warning: source files differ: pyproject={pyproject}, "
                f"package={package}, config={config_ver}"
            )
    except Exception as e:
        print(f"  Warning: could not check file consistency: {e}")

    # 4. No duplicate tag
    tag_name = f"v{new_version}"
    existing = subprocess.run(
        ["git", "tag", "-l", tag_name],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if existing:
        raise SystemExit(f"  Tag {tag_name} already exists")
    print(f"  Tag {tag_name} does not exist yet")

    print(f"All pre-checks passed for {new_version}")


if __name__ == "__main__":
    main()
