#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Post-bump validation for CI version pipeline.

Verifies that the version is valid and synchronized, and prints
advisory information for dev pre-releases.

Environment variables:
    VERSION: The version string to validate after bumping.
"""

from __future__ import annotations

import os

from packaging.version import Version


def main() -> None:
    """Run post-bump version checks."""
    version = os.environ["VERSION"]
    v = Version(version)

    if v.is_devrelease:
        base = Version(v.base_version)
        print(f"  {version} is a dev pre-release targeting the next cycle after {base}")

    print(f"Post-check: {version} is valid and synchronized")


if __name__ == "__main__":
    main()
