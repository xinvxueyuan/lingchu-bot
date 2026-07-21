"""Runtime hook registration package.

Importing this package makes the hook adapter layer, interface types and
handler modules available. Individual handler modules register themselves
with NoneBot when they are imported.
"""

from __future__ import annotations

from . import (
    adapters as adapters,
    handlers as handlers,
    interfaces as interfaces,
)

__all__ = ["adapters", "handlers", "interfaces"]
