"""LLBot (LLOneBot) protocol-implementation-private handlers.

APIs in this package exist only on LLBot and are **not** part of the standard
OneBot V11 API surface. They MUST be reached through the ``default/`` middle
layer, which resolves the protocol implementation before dispatching.

See ``AGENTS.md`` → "Protocol-private APIs live in their own layer".
"""

from . import mute_list as mute_list
