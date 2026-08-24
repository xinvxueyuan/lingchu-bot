"""Tests for the uv-semantics version bump argument derivation."""

from __future__ import annotations

from packaging.version import Version
import pytest

from scripts import ci_version_bump_args


@pytest.mark.parametrize(
    ("latest", "level", "pre", "expected"),
    [
        # Stable -> pre-release: uv requires a release component bump.
        ("1.0.0", "minor", "dev", ["--bump", "minor", "--bump", "dev"]),
        ("1.0.0", "patch", "dev", ["--bump", "patch", "--bump", "dev"]),
        ("1.0.0", "major", "dev", ["--bump", "major", "--bump", "dev"]),
        ("1.0.0", "patch", "alpha", ["--bump", "patch", "--bump", "alpha"]),
        ("1.0.0", "patch", "beta", ["--bump", "patch", "--bump", "beta"]),
        ("1.0.0", "patch", "rc", ["--bump", "patch", "--bump", "rc"]),
        # Stable -> stable: bump the release component (uv rejects --bump stable).
        ("1.0.0", "patch", "stable", ["--bump", "patch"]),
        ("1.0.0", "minor", "stable", ["--bump", "minor"]),
        ("1.0.0", "major", "stable", ["--bump", "major"]),
        # dev pre-release -> dev: continue the cycle at patch level.
        ("1.0.1.dev3", "patch", "dev", ["--bump", "dev"]),
        # dev pre-release -> dev at a higher level: new cycle.
        ("1.0.1.dev3", "minor", "dev", ["--bump", "minor", "--bump", "dev"]),
        ("1.0.1.dev3", "major", "dev", ["--bump", "major", "--bump", "dev"]),
        # dev pre-release -> stable: clear dev (patch) or bump level (minor/major).
        ("1.0.1.dev3", "patch", "stable", ["--bump", "stable"]),
        ("1.0.1.dev3", "minor", "stable", ["--bump", "minor"]),
        ("1.0.1.dev3", "major", "stable", ["--bump", "major"]),
        # dev pre-release -> alpha/beta/rc: convert on the same base at patch level.
        ("1.0.1.dev3", "patch", "alpha", ["--bump", "alpha"]),
        ("1.0.1.dev3", "patch", "beta", ["--bump", "beta"]),
        ("1.0.1.dev3", "patch", "rc", ["--bump", "rc"]),
        # dev pre-release -> pre at a higher level: new cycle.
        ("1.0.1.dev3", "minor", "alpha", ["--bump", "minor", "--bump", "alpha"]),
        ("1.0.1.dev3", "major", "rc", ["--bump", "major", "--bump", "rc"]),
        # alpha pre-release -> alpha: continue the cycle at patch level.
        ("1.0.1a1", "patch", "alpha", ["--bump", "alpha"]),
        # alpha pre-release -> alpha at a higher level: new cycle.
        ("1.0.1a1", "minor", "alpha", ["--bump", "minor", "--bump", "alpha"]),
        # alpha pre-release -> beta/rc: upgrade conversion on the same base.
        ("1.0.1a1", "patch", "beta", ["--bump", "beta"]),
        ("1.0.1a1", "patch", "rc", ["--bump", "rc"]),
        # alpha pre-release -> dev: needs a release component bump.
        ("1.0.1a1", "patch", "dev", ["--bump", "patch", "--bump", "dev"]),
        # beta pre-release -> beta: continue the cycle.
        ("1.0.1b1", "patch", "beta", ["--bump", "beta"]),
        # beta pre-release -> rc: upgrade conversion.
        ("1.0.1b1", "patch", "rc", ["--bump", "rc"]),
        # beta pre-release -> alpha: downgrade conversion needs a release bump.
        ("1.0.1b1", "patch", "alpha", ["--bump", "patch", "--bump", "alpha"]),
        # rc pre-release -> rc: continue the cycle.
        ("1.0.1rc1", "patch", "rc", ["--bump", "rc"]),
        # rc pre-release -> rc at a higher level: new cycle.
        ("1.0.1rc1", "minor", "rc", ["--bump", "minor", "--bump", "rc"]),
        # rc pre-release -> stable: clear rc (patch) or bump level (minor/major).
        ("1.0.1rc1", "patch", "stable", ["--bump", "stable"]),
        ("1.0.1rc1", "minor", "stable", ["--bump", "minor"]),
        # rc pre-release -> alpha/beta: downgrade conversion needs a release bump.
        ("1.0.1rc1", "patch", "alpha", ["--bump", "patch", "--bump", "alpha"]),
        ("1.0.1rc1", "patch", "beta", ["--bump", "patch", "--bump", "beta"]),
        # rc pre-release -> dev: needs a release component bump.
        ("1.0.1rc1", "patch", "dev", ["--bump", "patch", "--bump", "dev"]),
    ],
)
def test_derive_bump_args(
    latest: str,
    level: str,
    pre: str,
    expected: list[str],
) -> None:
    assert (
        ci_version_bump_args.derive_bump_args(Version(latest), level, pre) == expected
    )


def test_derive_bump_args_empty_latest_treated_as_stable_zero() -> None:
    # No tags yet: the baseline is the stable 0.0.0, so a pre-release bump
    # needs a release component.
    assert ci_version_bump_args.derive_bump_args(Version("0.0.0"), "patch", "dev") == [
        "--bump",
        "patch",
        "--bump",
        "dev",
    ]
    assert ci_version_bump_args.derive_bump_args(
        Version("0.0.0"), "minor", "stable"
    ) == [
        "--bump",
        "minor",
    ]


@pytest.mark.parametrize(
    ("level", "pre"),
    [
        ("invalid", "dev"),
        ("patch", "invalid"),
        ("", "dev"),
        ("patch", ""),
    ],
)
def test_main_rejects_invalid_input(
    level: str,
    pre: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        ci_version_bump_args.main(["1.0.0", level, pre])
    assert excinfo.value.code == 2
    assert capsys.readouterr().err


def test_main_prints_space_separated_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ci_version_bump_args.main(["1.0.0", "minor", "dev"])
    assert capsys.readouterr().out.strip() == "--bump minor --bump dev"


def test_main_requires_three_arguments() -> None:
    with pytest.raises(SystemExit):
        ci_version_bump_args.main(["1.0.0", "minor"])
