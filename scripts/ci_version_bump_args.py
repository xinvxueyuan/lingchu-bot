#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Derive ``uv version --bump`` arguments from the latest tag + bump intent.

Single source of truth for version bump semantics, based on uv's official
documentation (``docs.astral.sh/uv/guides/package/#updating-your-version``)
and verified against uv CLI behavior (uv 0.12.x). Replaces the fragile bash
string-matching logic that previously lived in ``Taskfile.yml::ci:version:bump``.

Key uv semantics encoded here:

- stable -> pre-release requires a release component bump (``--bump patch --bump beta``).
- pre-release -> same type continues the cycle (``--bump alpha`` on ``1.0.1a1`` -> ``1.0.1a2``).
- pre-release -> higher type converts on the same base (``--bump beta`` on ``1.0.1a1`` -> ``1.0.1b1``).
- pre-release -> lower type needs a release component bump (``--bump patch --bump alpha`` on ``1.0.1rc1``).
- pre-release -> dev needs a release component bump (``--bump patch --bump dev``).
- pre-release -> stable clears the pre-release (``--bump stable``); a non-patch
  level bumps the release component and clears the pre-release (``--bump minor``).
- ``--bump stable`` cannot be combined with another ``--bump`` value.

Usage:
    python scripts/ci_version_bump_args.py <latest_version> <bump_level> <bump_prerelease>

Prints one argument per line (e.g. ``--bump`` / ``minor`` / ``--bump`` / ``dev``)
so bash can read them with ``mapfile -t``.
"""

from __future__ import annotations

import sys

from packaging.version import Version

_LEVELS = frozenset({"major", "minor", "patch"})
_PRERELEASES = frozenset({"dev", "alpha", "beta", "rc", "stable"})
# PEP 440 pre-release ordering: alpha < beta < rc.
_PRE_PRIORITY = {"a": 0, "b": 1, "rc": 2}
# Map the CLI pre-release names to PEP 440 short labels used by Version.pre.
_PRE_LABEL = {"alpha": "a", "beta": "b", "rc": "rc"}
_ARG_COUNT = 3


def derive_bump_args(latest: Version, level: str, pre: str) -> list[str]:
    """Return the uv ``--bump`` argument sequence for the given intent."""
    # 1. stable bump
    if pre == "stable":
        if latest.is_prerelease:
            if level == "patch":
                # Clear the pre-release onto the current base (1.0.1.dev3 -> 1.0.1).
                return ["--bump", "stable"]
            # Bump the release component and clear the pre-release (1.0.1.dev3
            # + minor -> 1.1.0). uv's `--bump minor` already clears dev.
            return ["--bump", level]
        # Stable -> next stable at the requested level (1.0.0 + patch -> 1.0.1).
        return ["--bump", level]

    # 2. Stable -> pre-release: uv requires a release component bump.
    if not latest.is_prerelease:
        return ["--bump", level, "--bump", pre]

    # 3. Latest is a pre-release.
    if latest.is_devrelease:
        if level == "patch" and pre == "dev":
            # Continue the dev cycle (1.0.1.dev3 -> 1.0.1.dev4).
            return ["--bump", "dev"]
        if pre == "dev":
            # dev -> dev at a higher level starts a new cycle (minor+dev).
            return ["--bump", level, "--bump", "dev"]
        if level == "patch":
            # dev -> alpha/beta/rc converts onto the same base (1.0.1.dev3
            # + alpha -> 1.0.1a1).
            return ["--bump", pre]
        # dev -> pre at a higher level starts a new cycle (minor+alpha).
        return ["--bump", level, "--bump", pre]

    # 4. Latest is alpha/beta/rc.
    if latest.pre is None:  # pragma: no cover - is_prerelease implies pre is set
        return ["--bump", level, "--bump", pre]
    latest_pre = latest.pre[0]  # 'a' | 'b' | 'rc'
    pre_label = _PRE_LABEL.get(pre)  # None when pre == "dev"
    if pre_label is not None and latest_pre == pre_label:
        if level == "patch":
            # Same type continues the cycle (1.0.1a1 + alpha -> 1.0.1a2).
            return ["--bump", pre]
        # Same type at a higher level starts a new cycle (minor+alpha).
        return ["--bump", level, "--bump", pre]
    if pre == "dev":
        # alpha/beta/rc -> dev needs a release component bump.
        return ["--bump", level, "--bump", "dev"]
    if pre_label is None:  # pragma: no cover - pre == "dev" handled above
        return ["--bump", level, "--bump", pre]
    if _PRE_PRIORITY[pre_label] > _PRE_PRIORITY[latest_pre]:
        if level == "patch":
            # Upgrade conversion on the same base (a -> b -> rc).
            return ["--bump", pre]
        # Upgrade conversion at a higher level starts a new cycle.
        return ["--bump", level, "--bump", pre]
    # Downgrade conversion (rc -> a, rc -> b, b -> a) needs a release bump.
    return ["--bump", level, "--bump", pre]


def main(argv: list[str]) -> None:
    """Print the derived uv ``--bump`` arguments, one per line."""
    if len(argv) != _ARG_COUNT:
        print(
            "usage: ci_version_bump_args.py <latest_version> <bump_level> <bump_prerelease>",
            file=sys.stderr,
        )
        raise SystemExit(2)
    latest_raw, level, pre = argv
    if level not in _LEVELS:
        print(
            f"invalid bump_level: {level!r} (expected major|minor|patch)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if pre not in _PRERELEASES:
        print(
            f"invalid bump_prerelease: {pre!r} (expected dev|alpha|beta|rc|stable)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    # An empty latest (no tags yet) is treated as the stable 0.0.0 baseline.
    latest = Version(latest_raw) if latest_raw else Version("0.0.0")
    # Single space-separated line so bash can read it with `read -ra` without
    # needing `tr` (unavailable on Windows).
    print(" ".join(derive_bump_args(latest, level, pre)))


if __name__ == "__main__":
    main(sys.argv[1:])
