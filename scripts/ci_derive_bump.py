#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Derive BUMP_LEVEL and BUMP_PRERELEASE from a branch name or dispatch input.

Single source of truth for the seven release bumps plus dev-* branch mapping.
Called by:

- ``.github/workflows/ci-builds.yml::versioned-build`` (dev branches)
- ``.github/workflows/release.yml::validate`` (manual-trigger ``workflow_dispatch`` ``bump`` input)
- ``Taskfile.yml::release:prepare`` (local release scaffolding)
- ``Taskfile.yml::release:notes`` (local notes scaffolding)

Inputs:

- ``<bare-bump>``         -> derives from the seven release bump names (``workflow_dispatch`` input / local ``BUMP`` var)
- ``releases/<bump>``     -> same as the bare bump (legacy branch-name form, still accepted for compatibility)
- ``dev[-minor|-major]-*`` -> derives from dev-* branch conventions
- ``main`` / ``dev``      -> patch + dev (default development bump)

Outputs (one per line, KEY=VALUE):

- ``bump_level=major|minor|patch``
- ``bump_prerelease=dev|alpha|beta|rc|stable``
"""

from __future__ import annotations

import re
import sys

# Release bumps: branch name (after ``releases/``) or workflow_dispatch input.
RELEASE_BUMPS: dict[str, tuple[str, str]] = {
    "major": ("major", "dev"),
    "minor": ("minor", "dev"),
    "patch": ("patch", "dev"),
    "stable": ("patch", "stable"),
    "alpha": ("patch", "alpha"),
    "beta": ("patch", "beta"),
    "rc": ("patch", "rc"),
}

# Pre-release suffix patterns for dev-* branches.  Anchored at the start of
# the branch name; optional level prefix (``dev-minor-``, ``dev-major-``) is
# captured by the optional group so the same regex works for all levels.
_DEV_PRERELEASE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^dev(-minor|-major)?-alpha", "alpha"),
    (r"^dev(-minor|-major)?-beta", "beta"),
    (r"^dev(-minor|-major)?-rc", "rc"),
    (r"^dev(-minor|-major)?-stable", "stable"),
)


def derive_release(bump: str) -> tuple[str, str]:
    """Resolve a release-bump name (or branch-suffix) to level + prerelease."""
    if bump not in RELEASE_BUMPS:
        expected = ", ".join(RELEASE_BUMPS)
        raise SystemExit(
            f"Invalid release bump: {bump!r} (expected one of: {expected})"
        )
    return RELEASE_BUMPS[bump]


def derive_dev(branch: str) -> tuple[str, str]:
    """Resolve a dev-* branch name to level + prerelease."""
    if branch.startswith("dev-major"):
        level = "major"
    elif branch.startswith("dev-minor"):
        level = "minor"
    else:
        level = "patch"

    for pattern, pre in _DEV_PRERELEASE_PATTERNS:
        if re.match(pattern, branch):
            return level, pre
    return level, "dev"


def derive(source: str) -> tuple[str, str]:
    """Dispatch between release and dev branch conventions."""
    if source.startswith("releases/"):
        return derive_release(source.removeprefix("releases/"))
    if source.startswith("dev-") or source in {"main", "dev"}:
        return derive_dev(source)
    # Bare bump name (workflow_dispatch input).
    return derive_release(source)


def main(argv: list[str]) -> None:
    # argv[0] is the script name, so we need at least one positional argument.
    if len(argv) < 1 + 1:
        raise SystemExit(
            "usage: ci_derive_bump.py <release-bump | dev-branch | releases/<bump>>"
        )
    level, pre = derive(argv[1])
    print(f"bump_level={level}")
    print(f"bump_prerelease={pre}")


if __name__ == "__main__":
    main(sys.argv)
