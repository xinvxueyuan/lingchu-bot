#!/usr/bin/env python3
"""Container entrypoint for Lingchu Bot smoke tests.

The script starts NoneBot via ``nb run``, waits for the application to report
``Application startup complete.``, then imports and executes the smoke checks
from ``tests/smoke/``. A JUnit-style XML report is written to
``/app/smoke-test-results.xml`` (override with ``SMOKE_TEST_RESULTS_XML``).
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
from xml.etree.ElementTree import Element, SubElement, tostring

import nonebot

# Ensure the source tree and test helpers are importable both in the container
# (PYTHONPATH=/app) and when running the script from the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT / "tests"))

_LOGGER = logging.getLogger("smoke-test")

_STARTUP_MARKER = "Application startup complete."
_STARTUP_TIMEOUT_SECONDS = 120
_SHUTDOWN_TIMEOUT_SECONDS = 15


def _init_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def _init_nonebot() -> None:
    """Initialize NoneBot and load the Lingchu plugin without starting the driver.

    This gives the smoke-check process its own plugin instance so it can
    inspect hook registries and call service initializers independently of the
    ``nb run`` subprocess.
    """
    try:
        nonebot.get_driver()
    except ValueError:
        pass
    else:
        return

    init_config: dict[str, object] = {
        "LOCALSTORE_USE_CWD": "True",
        "DRIVER": "~fastapi+~httpx+~websockets",
        "lingchu_adapter": "~onebot.v11",
        "LINGCHU_SUPERUSERS": {"user1": {"qq": "42"}},
        "lingchu_locale": "zh_CN",
    }
    sqlalchemy_url = os.environ.get("SQLALCHEMY_DATABASE_URL")
    if sqlalchemy_url:
        init_config["SQLALCHEMY_DATABASE_URL"] = sqlalchemy_url
    nonebot.init(**init_config)

    driver = nonebot.get_driver()
    from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

    driver.register_adapter(ONEBOT_V11Adapter)
    nonebot.load_from_toml("pyproject.toml")


def _run_migrations() -> bool:
    """Run ``nb orm upgrade`` so the smoke-test starts with an up-to-date schema."""
    _LOGGER.info("Running database migrations with 'nb orm upgrade'")
    process = subprocess.run(
        ["nb", "orm", "upgrade"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    sys.stdout.write(process.stdout)
    sys.stdout.flush()
    if process.returncode != 0:
        _LOGGER.error("Migration failed with exit code %d", process.returncode)
        return False
    _LOGGER.info("Migrations completed successfully")
    return True


def _start_nonebot_subprocess() -> subprocess.Popen[str]:
    """Start ``nb run`` and stream its combined stdout/stderr."""
    return subprocess.Popen(
        ["nb", "run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _wait_for_startup(
    process: subprocess.Popen[str],
    timeout: float = _STARTUP_TIMEOUT_SECONDS,
) -> bool:
    """Read subprocess output until the startup marker appears or timeout."""
    deadline = time.monotonic() + timeout
    stdout = process.stdout
    if stdout is None:
        _LOGGER.error("Subprocess stdout is not available")
        return False

    for line in stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if time.monotonic() > deadline:
            _LOGGER.error("Timeout waiting for NoneBot startup marker")
            return False
        if _STARTUP_MARKER in line:
            _LOGGER.info("NoneBot startup marker detected")
            return True

    _LOGGER.error("NoneBot subprocess exited before startup marker")
    return False


def _terminate_process(process: subprocess.Popen[str]) -> None:
    """Gracefully terminate the subprocess, killing it if necessary."""
    if process.poll() is not None:
        return

    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _LOGGER.warning("Subprocess did not terminate in time, sending SIGKILL")
        process.kill()
        process.wait()


async def _run_checks() -> list[dict[str, object]]:
    """Import and execute each smoke check, collecting pass/fail metadata."""
    from tests.smoke.test_bot_startup import check_bot_startup
    from tests.smoke.test_core_services import check_core_services
    from tests.smoke.test_hook_registration import check_hook_registration

    checks: list[tuple[str, object]] = [
        ("test_bot_startup", check_bot_startup),
        ("test_hook_registration", check_hook_registration),
        ("test_core_services", check_core_services),
    ]

    results: list[dict[str, object]] = []
    for name, check in checks:
        start = time.monotonic()
        error: Exception | None = None
        try:
            await check()
        except Exception as exc:  # noqa: BLE001
            error = exc
        duration = time.monotonic() - start
        results.append({
            "name": name,
            "error": error,
            "duration": duration,
        })
    return results


def _write_junit_xml(
    results: list[dict[str, object]],
    output_path: Path,
) -> None:
    """Write a minimal JUnit XML report with one testcase per smoke check."""
    failures = sum(1 for result in results if result["error"] is not None)
    testsuites = Element("testsuites")
    testsuite = SubElement(
        testsuites,
        "testsuite",
        {
            "name": "smoke-tests",
            "tests": str(len(results)),
            "failures": str(failures),
        },
    )

    for result in results:
        error = result["error"]
        duration = float(result["duration"])
        testcase = SubElement(
            testsuite,
            "testcase",
            {
                "name": str(result["name"]),
                "time": f"{duration:.3f}",
            },
        )
        if error is not None:
            failure = SubElement(
                testcase,
                "failure",
                {"message": f"{type(error).__name__}: {error}"},
            )
            failure.text = "".join(traceback.format_exception(error))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        tostring(testsuites, encoding="unicode"),
        encoding="utf-8",
    )


def _ensure_smoke_env() -> None:
    """Provide minimal required config when the env file is empty."""
    if not os.environ.get("LINGCHU_SUPERUSERS"):
        os.environ["LINGCHU_SUPERUSERS"] = '{"smoke_user":{"qq":"42"}}'


async def _async_main() -> int:
    """Run the smoke test workflow and return an exit code."""
    output_path = Path(
        os.environ.get("SMOKE_TEST_RESULTS_XML", "/app/smoke-test-results.xml")
    )

    _ensure_smoke_env()

    if not _run_migrations():
        results: list[dict[str, object]] = [
            {
                "name": "test_bot_startup",
                "error": RuntimeError("Database migration failed"),
                "duration": 0.0,
            }
        ]
        _write_junit_xml(results, output_path)
        return 1

    process = _start_nonebot_subprocess()
    try:
        if not _wait_for_startup(process):
            results: list[dict[str, object]] = [
                {
                    "name": "test_bot_startup",
                    "error": RuntimeError("NoneBot did not reach startup marker"),
                    "duration": 0.0,
                }
            ]
            _write_junit_xml(results, output_path)
            return 1

        _init_nonebot()
        results = await _run_checks()
    finally:
        _terminate_process(process)

    _write_junit_xml(results, output_path)

    failed = [result for result in results if result["error"] is not None]
    if failed:
        for result in failed:
            error = result["error"]
            _LOGGER.error("FAIL %s: %s", result["name"], error)
        return 1

    _LOGGER.info("All %d smoke check(s) passed", len(results))
    return 0


def main() -> int:
    """Synchronous wrapper around the async smoke test workflow."""
    _init_logging()
    return asyncio.run(_async_main())


if __name__ == "__main__":
    sys.exit(main())
