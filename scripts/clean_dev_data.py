"""Remove disposable local development data without touching source files."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

RUNTIME_DIRECTORIES: tuple[str, ...] = ("data", "config", "cache")
ARTIFACT_DIRECTORIES: tuple[str, ...] = (
    ".pytest-localstore",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "playwright-report",
    "test-results",
)
ARTIFACT_FILES: tuple[str, ...] = (".coverage", "coverage.xml")
ARTIFACT_FILE_PATTERNS: tuple[str, ...] = (".coverage.*",)
PYTHON_CACHE_ROOTS: tuple[str, ...] = ("src", "tests", "scripts")


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_targets(root: Path, *, include_artifacts: bool) -> Iterable[Path]:
    for relative_path in RUNTIME_DIRECTORIES:
        yield root / relative_path

    if not include_artifacts:
        return

    for relative_path in ARTIFACT_DIRECTORIES + ARTIFACT_FILES:
        yield root / relative_path
    for pattern in ARTIFACT_FILE_PATTERNS:
        yield from sorted(root.glob(pattern))
    for relative_root in PYTHON_CACHE_ROOTS:
        cache_root = root / relative_root
        if cache_root.is_dir():
            yield from sorted(cache_root.glob("**/__pycache__"))


def _validate_target(root: Path, target: Path) -> Path:
    root = root.resolve()
    candidate = target.absolute()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(
            f"refusing to operate outside repository: {candidate}"
        ) from exc
    if candidate == root:
        raise RuntimeError("refusing to operate on the repository root")

    # A parent directory may be a symlink pointing outside the repository,
    # making the candidate itself not a symlink while its resolved path
    # escapes the root (e.g. repo/src -> /outside, repo/src/pkg/__pycache__).
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(
            f"refusing to follow path outside repository: {candidate}"
        ) from exc
    if resolved == root:
        raise RuntimeError("refusing to operate on the repository root")
    return candidate


def _remove_target(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def clean_dev_data(*, apply: bool, include_artifacts: bool) -> int:
    """Print or remove disposable development targets under the repository."""
    root = _repository_root()
    removed_count = 0
    for raw_target in _iter_targets(root, include_artifacts=include_artifacts):
        target = _validate_target(root, raw_target)
        if not target.exists() and not target.is_symlink():
            continue

        relative_target = target.relative_to(root)
        if apply:
            _remove_target(target)
            print(f"Removed {relative_target}")
        else:
            print(f"Would remove {relative_target}")
        removed_count += 1
    return removed_count


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean disposable Lingchu Bot development data."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform deletion; without this flag the command is a dry-run",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm deletion together with --apply",
    )
    parser.add_argument(
        "--include-artifacts",
        action="store_true",
        help="also remove disposable test, coverage and build artifacts",
    )
    args = parser.parse_args()
    if args.yes and not args.apply:
        parser.error("--yes requires --apply")
    if args.apply and not args.yes:
        parser.error("--apply requires --yes")
    return args


def main() -> int:
    """Run the development-data cleanup command."""
    args = _parse_args()
    if not args.apply:
        print("Dry-run only; pass --apply --yes to delete the listed targets.")
    try:
        count = clean_dev_data(
            apply=args.apply,
            include_artifacts=args.include_artifacts,
        )
    except OSError as exc:
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        return 1
    print(f"Processed {count} target(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
