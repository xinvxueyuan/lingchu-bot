"""Logging configuration for Lingc CLI."""

from __future__ import annotations

import logging
import sys

_LOGGER_NAME = "lingc_cli"


def configure_logging(*, verbose: bool = False) -> None:
    """Configure the CLI logger to stream to stderr."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def get_logger(name: str = "") -> logging.Logger:
    """Return the CLI logger (optionally namespaced)."""
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)
