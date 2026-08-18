"""Submit the continuation config to CircleCI's dynamic-config API.

Called by the preflight job after `scripts/ci_gh_preflight.py` decides whether
GitHub Actions is healthy. Reads `CIRCLE_CONTINUATION_KEY` (injected by
CircleCI into every setup pipeline) and POSTs the given YAML configuration to
`/api/v2/pipeline/continue` -- the same endpoint the removed `circleci
continuation continue` CLI command used to hit (newer circleci-cli versions no
longer ship the `continuation` subcommand).

Usage:
    python3 scripts/ci_gh_continue.py --config .circleci/checks.yml
    python3 scripts/ci_gh_continue.py --config .circleci/skip.yml
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import TYPE_CHECKING
import urllib.error
import urllib.request

if TYPE_CHECKING:
    from collections.abc import Sequence

CONTINUATION_URL = "https://circleci.com/api/v2/pipeline/continue"
TIMEOUT_SECONDS = 30


def main(argv: Sequence[str] | None = None) -> int:
    """POST the continuation config and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", required=True, help="YAML config file to continue with"
    )
    args = parser.parse_args(argv)

    key = os.environ.get("CIRCLE_CONTINUATION_KEY", "")
    if not key:
        print("error: CIRCLE_CONTINUATION_KEY is not set", file=sys.stderr)
        return 1

    try:
        config_text = pathlib.Path(args.config).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        return 1

    payload = json.dumps({
        "continuation-key": key,
        "configuration": config_text,
    }).encode()
    request = urllib.request.Request(
        CONTINUATION_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            print(f"Continuation accepted (HTTP {response.status}).")
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"Continuation failed (HTTP {exc.code}): {body}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"Continuation request failed ({exc!r})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
