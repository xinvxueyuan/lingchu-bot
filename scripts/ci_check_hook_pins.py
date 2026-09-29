#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Verify ``prek.toml`` hook pins stay aligned with ``uv.lock``.

``prek.toml`` is the only pre-commit hook source of truth in this repository
(``.pre-commit-config.yaml`` is explicitly abandoned), so the official
pre-commit ecosystem — which only reads ``.pre-commit-config.yaml`` — never
bumps these ``rev`` pins. Without a guard the locally executed ruff/ty hooks
silently fall behind the versions locked in ``uv.lock``, and the hooks behave
differently from CI for byte-identical source.

This script closes that gap: it reads the ``ruff`` / ``ty`` versions resolved
by ``uv.lock`` and asserts the matching ``prek.toml`` pins agree. Repos with
no ``uv.lock`` counterpart (``pre-commit/pre-commit-hooks``) are only checked
for pin-comment syntax.

Usage:
    python scripts/ci_check_hook_pins.py

Exit codes:
    0  every checked pin matches ``uv.lock``
    1  drift, a malformed pin, or an ambiguous ``uv.lock`` entry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import sys
import tomllib

# Hook repos whose ``rev`` is derived from a ``uv.lock`` package version.
# Anything absent here has no uv tool counterpart and is syntax-checked only.
TRACKED_HOOK_REPOS: dict[str, str] = {
    "astral-sh/ruff-pre-commit": "ruff",
    "astral-sh/ty-pre-commit": "ty",
}

PREK_CONFIG = Path("prek.toml")
UV_LOCK = Path("uv.lock")

_REPO_LINE = re.compile(r'^repo\s*=\s*"(?P<repo>[^"]+)"\s*(?:#.*)?$')
_REV_LINE = re.compile(r'^rev\s*=\s*"(?P<rev>[^"]*)"\s*(?P<comment>#.*)?$')
_PIN_COMMENT = re.compile(r"^#\s*pinned from (?P<slug>[^@\s]+)@(?P<tag>\S+)\s*$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_GITHUB_SLUG = re.compile(r"github\.com/(?P<slug>[^/]+/[^/]+?)(?:\.git)?/?$")


@dataclass(frozen=True)
class HookPin:
    """One ``rev`` declaration from ``prek.toml``, with its owning ``repo``."""

    line: int
    repo: str | None
    rev: str
    comment: str | None


@dataclass
class PinVerdict:
    """What one pin check found: format problems and/or version drift."""

    problems: list[str] = field(default_factory=list)
    drift: str | None = None
    matched: str | None = None


def read_hook_pins(path: Path) -> list[HookPin]:
    """Parse every ``repo`` + ``rev`` pair declared in ``prek.toml``."""
    pins: list[HookPin] = []
    repo: str | None = None
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()

        repo_match = _REPO_LINE.match(line)
        if repo_match:
            repo = repo_match.group("repo")
            continue

        rev_match = _REV_LINE.match(line)
        if rev_match:
            pins.append(
                HookPin(
                    line=lineno,
                    repo=repo,
                    rev=rev_match.group("rev"),
                    comment=rev_match.group("comment"),
                )
            )
    return pins


def collect_lock_versions(lock_path: Path) -> dict[str, list[str]]:
    """Group every ``[[package]]`` version declared in ``uv.lock`` by name."""
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    versions: dict[str, list[str]] = {}
    for entry in lock.get("package", []):
        name = entry.get("name")
        version = entry.get("version")
        if isinstance(name, str) and isinstance(version, str):
            versions.setdefault(name, []).append(version)
    return versions


def resolve_lock_version(
    versions: dict[str, list[str]],
    package: str,
) -> tuple[str | None, list[str]]:
    """Resolve the single locked ``package`` version, refusing ambiguity."""
    found = sorted(set(versions.get(package, [])))
    if not found:
        return None, [f"{UV_LOCK} declares no package named {package!r}"]
    if len(found) > 1:
        return None, [
            f"{UV_LOCK} resolves {package!r} to multiple versions "
            f"({', '.join(found)}) — collapse the duplicate lock entry first, "
            "the hook pin cannot be derived from an ambiguous version set"
        ]
    return found[0], []


def describe_drift(
    pin: HookPin,
    slug: str,
    pinned_tag: str,
    package: str,
    locked_version: str,
) -> str:
    """Render a copy-pasteable repair recipe for one drifted pin."""
    expected_tag = f"v{locked_version}"
    url = f"https://github.com/{slug}"
    return "\n".join((
        f"{slug}: {PREK_CONFIG}:{pin.line} pins {pinned_tag} but {UV_LOCK} "
        f"resolves {package} {locked_version}",
        f"  expected tag: {expected_tag}",
        "  fix: replace this pin in prek.toml with",
        f'       rev = "<40-hex-sha>"  # pinned from {slug}@{expected_tag}',
        "  resolve the SHA with (pin the `^{}` commit line, never the "
        "annotated tag object):",
        f"    git ls-remote {url} refs/tags/{expected_tag} "
        f'"refs/tags/{expected_tag}^{{}}"',
    ))


def check_pin(pin: HookPin, locked: dict[str, str]) -> PinVerdict:
    """Validate one pin's syntax and, when tracked, its ``uv.lock`` tag."""
    verdict = PinVerdict()
    where = f"{PREK_CONFIG}:{pin.line}"

    if pin.repo is None:
        verdict.problems.append(f"{where}: `rev` appears before any `repo` entry")

    if not _COMMIT_SHA.match(pin.rev):
        verdict.problems.append(
            f"{where}: rev {pin.rev!r} is not a 40-char hex commit SHA "
            "(pin the commit, never the annotated tag object)"
        )

    if pin.comment is None:
        verdict.problems.append(
            f"{where}: missing `# pinned from <owner>/<repo>@<tag>` comment "
            f'next to rev = "{pin.rev}"'
        )
        return verdict

    comment_match = _PIN_COMMENT.match(pin.comment)
    if comment_match is None:
        verdict.problems.append(
            f"{where}: comment {pin.comment!r} does not match "
            "`# pinned from <owner>/<repo>@<tag>`"
        )
        return verdict

    slug = comment_match.group("slug")
    if pin.repo is not None:
        repo_match = _GITHUB_SLUG.search(pin.repo)
        repo_slug = repo_match.group("slug") if repo_match else pin.repo
        if repo_slug != slug:
            verdict.problems.append(
                f"{where}: comment names {slug} but `repo` is {pin.repo}"
            )

    package = TRACKED_HOOK_REPOS.get(slug)
    if package is None or package not in locked:
        # Untracked repo (no uv tool counterpart), or a lock lookup that
        # already failed in ``main``: only the comment shape is enforced.
        return verdict

    pinned_tag = comment_match.group("tag")
    expected_tag = f"v{locked[package]}"
    if pinned_tag != expected_tag:
        verdict.drift = describe_drift(pin, slug, pinned_tag, package, locked[package])
    else:
        verdict.matched = f"{slug}@{pinned_tag} == {package} {locked[package]}"
    return verdict


def main() -> None:
    """Check every ``prek.toml`` pin and exit non-zero on any problem."""
    problems: list[str] = []
    drifts: list[str] = []
    matched: list[str] = []

    versions = collect_lock_versions(UV_LOCK)
    locked: dict[str, str] = {}
    for package in sorted(set(TRACKED_HOOK_REPOS.values())):
        version, issues = resolve_lock_version(versions, package)
        problems.extend(issues)
        if version is not None:
            locked[package] = version

    pins = read_hook_pins(PREK_CONFIG)
    if not pins:
        problems.append(f'{PREK_CONFIG} declares no `rev = "..."` pin')

    for pin in pins:
        verdict = check_pin(pin, locked)
        problems.extend(verdict.problems)
        if verdict.drift is not None:
            drifts.append(verdict.drift)
        if verdict.matched is not None:
            matched.append(verdict.matched)

    if drifts:
        print(f"Hook pin drift detected ({len(drifts)}):", file=sys.stderr)
        for drift in drifts:
            print(f"\n{drift}", file=sys.stderr)

    if problems:
        print(f"Hook pin format problems ({len(problems)}):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)

    if problems or drifts:
        raise SystemExit(1)

    print(f"✓ {PREK_CONFIG} hook pins match {UV_LOCK} ({'; '.join(matched)})")


if __name__ == "__main__":
    main()
