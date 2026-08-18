"""CircleCI preflight: decide whether GitHub Actions is healthy for the head commit.

Part of the dual-line CI (GitHub Actions primary, CircleCI watchdog). The
preflight job runs this script to inspect the GitHub Actions runs of the
current commit and answer: is GitHub healthy enough that CircleCI should stay
out, or did GitHub Actions fail entirely so CircleCI must take over the full
checks (`.circleci/checks.yml`)?

Decision matrix (stdout, exactly one line):

    gh-alive    at least one run is queued/in_progress, or concluded
                success/skipped -> GitHub Actions is alive; CircleCI
                continues as a no-op
    gh-down     all runs concluded failure/cancelled/timed_out, or no runs
                exist -> GitHub Actions is down/failed; CircleCI takes over
    gh-unknown  no token, or the GitHub API query failed -> cannot decide;
                fail open and take over the full checks

Only the Python standard library is used so this runs on any cimg image and
locally (e.g. `python3 scripts/ci_gh_preflight.py --dry-run <file>.json`).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import TYPE_CHECKING
import urllib.error
import urllib.request

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

REPO = "xinvxueyuan/lingchu-bot"
API_TIMEOUT_SECONDS = 20
USER_AGENT = "lingchu-bot-circleci-preflight"
ALIVE_STATUSES = {"queued", "in_progress"}
ALIVE_CONCLUSIONS = {"success", "skipped"}


def decide(runs: Sequence[dict[str, Any]]) -> str:
    """Map a workflow_runs list to gh-alive / gh-down per the decision matrix."""
    if not runs:
        return "gh-down"
    for run in runs:
        if run.get("status") in ALIVE_STATUSES:
            return "gh-alive"
        if run.get("conclusion") in ALIVE_CONCLUSIONS:
            return "gh-alive"
    return "gh-down"


def fetch_runs(sha: str, token: str, repo: str) -> list[dict[str, Any]]:
    """Query the GitHub Actions runs for a head commit via the REST API."""
    url = (
        f"https://api.github.com/repos/{repo}/actions/runs?head_sha={sha}&per_page=100"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    return payload.get("workflow_runs", [])


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, decide, and print the one-line decision."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", help="head commit SHA to query")
    parser.add_argument("--token", default="", help="GitHub token with actions: read")
    parser.add_argument("--repo", default=REPO, help="owner/repo to query")
    parser.add_argument(
        "--dry-run",
        metavar="JSON_FILE",
        help="decide from a local workflow_runs JSON file instead of the API (testing)",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        with pathlib.Path(args.dry_run).open(encoding="utf-8") as file:
            payload = json.load(file)
        runs = payload.get("workflow_runs", [])
        decision = decide(runs)
        print(f"dry-run: {len(runs)} runs -> {decision}", file=sys.stderr)
        print(decision)
        return 0

    if not args.sha:
        print(
            "error: --sha is required (or use --dry-run for testing)", file=sys.stderr
        )
        return 2
    if not args.token:
        print("no token: failing open (gh-unknown)", file=sys.stderr)
        print("gh-unknown")
        return 0

    try:
        runs = fetch_runs(args.sha, args.token, args.repo)
    except urllib.error.HTTPError as exc:
        print(
            f"GitHub API HTTP error {exc.code}: failing open (gh-unknown)",
            file=sys.stderr,
        )
        print("gh-unknown")
        return 0
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(
            f"GitHub API request failed ({exc!r}): failing open (gh-unknown)",
            file=sys.stderr,
        )
        print("gh-unknown")
        return 0

    decision = decide(runs)
    print(f"{len(runs)} workflow runs for {args.sha}: {decision}", file=sys.stderr)
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
