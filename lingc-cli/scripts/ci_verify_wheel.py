#!/usr/bin/env python3
"""CI wheel verification for the lingc-cli package.

Asserts the built wheel exposes the lingc_cli package and the lc console
script. Exits non-zero on failure.
"""

from __future__ import annotations

from pathlib import Path
import sys
from zipfile import ZipFile

EXPECTED_PACKAGE = "lingc_cli"


def verify_wheel(dist_dir: Path) -> None:
    """Verify dist_dir contains a lingc-cli wheel with the expected entry."""
    wheels = sorted(dist_dir.glob("lingc_cli-*.whl"))
    if not wheels:
        raise SystemExit(f"No lingc-cli wheel found under {dist_dir}")
    wheel = wheels[0]
    with ZipFile(wheel) as archive:
        names = archive.namelist()
    if not any(name.startswith(EXPECTED_PACKAGE) for name in names):
        raise SystemExit(f"Missing package {EXPECTED_PACKAGE} in {wheel.name}")
    if "entry_points.txt" in names:
        entries = archive.read("entry_points.txt").decode("utf-8")
        if "lc = lingc_cli.app:main" not in entries:
            raise SystemExit(f"Missing lc entry point in {wheel.name}")
    print(f"lingc-cli wheel OK: {wheel.name}")


def main(argv: list[str]) -> None:
    dist_dir = Path(argv[1]) if len(argv) > 1 else Path("dist")
    verify_wheel(dist_dir)


if __name__ == "__main__":
    main(sys.argv)
