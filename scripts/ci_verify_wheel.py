#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""CI wheel contents verification.

Asserts the built wheel exposes the Lingchu Bot top-level packages and the
staged WebUI static bundle. Exits non-zero if anything is missing, if the
bundle lacks an entry point or a JS asset, if source maps leaked into the
wheel, or if ``node_modules`` was packaged by accident.

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

# WebUI static bundle, staged by ``scripts/stage_webui.mjs`` before ``uv build``.
WEBUI_DIST_CLIENT: str = "nonebot_plugin_lingchu_bot/webui/dist/client/"
WEBUI_INDEX: str = f"{WEBUI_DIST_CLIENT}index.html"
WEBUI_ASSETS: str = f"{WEBUI_DIST_CLIENT}assets/"


def _verify_webui_bundle(names: list[str]) -> list[str]:
    """Check the staged WebUI bundle is present and clean.

    Args:
        names: Every member path inside the wheel.

    Returns:
        list[str]: Human-readable problems; empty when the bundle is healthy.

    """
    problems: list[str] = []
    if WEBUI_INDEX not in names:
        problems.append(f"missing WebUI entry point: {WEBUI_INDEX}")
    js_assets = [
        name for name in names if name.startswith(WEBUI_ASSETS) and name.endswith(".js")
    ]
    if not js_assets:
        problems.append(f"no JavaScript asset under {WEBUI_ASSETS}")
    source_maps = [
        name
        for name in names
        if name.startswith(WEBUI_DIST_CLIENT) and name.endswith(".map")
    ]
    if source_maps:
        problems.append(
            f"{len(source_maps)} source map(s) under {WEBUI_DIST_CLIENT}: "
            + ", ".join(source_maps[:5]),
        )
    node_modules = [name for name in names if "node_modules/" in name]
    if node_modules:
        problems.append(
            f"{len(node_modules)} node_modules/ path(s) packaged: "
            + ", ".join(node_modules[:5]),
        )
    return problems


def verify_wheel(dist_dir: Path) -> None:
    """Verify ``dist_dir`` contains a wheel that exposes ``EXPECTED_MODULES``.

    Args:
        dist_dir: Directory holding the built wheel.

    Raises:
        SystemExit: When no wheel exists, a module is missing, or the staged
            WebUI bundle is absent, empty, or contains leaked build inputs.

    """
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"No wheel found under {dist_dir}")
    wheel = wheels[0]
    with ZipFile(wheel) as z:
        names = z.namelist()
    missing = [m for m in EXPECTED_MODULES if not any(n.startswith(m) for n in names)]
    if missing:
        raise SystemExit(f"Missing modules in {wheel.name}: {', '.join(missing)}")
    print(f"\u2713 All modules present in wheel: {', '.join(EXPECTED_MODULES)}")

    problems = _verify_webui_bundle(names)
    if problems:
        details = "\n".join(f"  - {problem}" for problem in problems)
        raise SystemExit(
            f"WebUI bundle verification failed for {wheel.name}:\n{details}\n"
            "  Hint: run `pnpm webui:build && pnpm webui:stage` before `uv build` "
            "(`turbo run py:build` chains this automatically via dependsOn).",
        )
    print(f"\u2713 WebUI bundle present in wheel: {WEBUI_INDEX} (+ JS assets)")


def main(argv: list[str]) -> None:
    """Entry point.

    Args:
        argv: Process argv; ``argv[1]`` optionally overrides the dist directory.

    """
    dist_dir = Path(argv[1]) if len(argv) > 1 else Path("dist")
    verify_wheel(dist_dir)


if __name__ == "__main__":
    main(sys.argv)
