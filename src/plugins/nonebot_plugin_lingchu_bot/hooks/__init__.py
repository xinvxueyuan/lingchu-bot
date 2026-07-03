"""Runtime hook registration package.

Importing this package makes the hook adapter layer, interface types and
handler modules available. Individual handler modules register themselves
with NoneBot when they are imported.
"""

from __future__ import annotations

from . import adapters as adapters
from . import handlers as handlers
from . import interfaces as interfaces
from . import registry as registry

__all__ = ["adapters", "handlers", "interfaces", "registry"]
