"""Container-facing smoke tests for Lingchu Bot.

Tests in this package are designed to be importable and executable by
``docker/smoke-test.py`` inside the production container, without requiring
pytest or other test-only dependencies at runtime.
"""

from __future__ import annotations
