---
name: protocol-endpoint-operations
description: Use when adding or changing Lingchu Bot commands that operate on protocol-side runtimes, adapter processes, connection lifecycle, reconnect feedback, or OneBot/NapCat operational APIs.
---

# Protocol Endpoint Operations

## Core Rule

Protocol-side operations cross a live connection boundary. Keep every command surface synchronized, and prove adapter API plus reconnect behavior with runtime evidence.

## Workflow

1. In Linux/WSL automation, source shell rc before declaring tools missing:
   `source ~/.zshrc >/dev/null 2>&1 || source ~/.bashrc >/dev/null 2>&1 || true`.
2. Run `git status --short`; preserve unrelated user changes.
3. Before symbol edits, run GitNexus impact analysis and report direct callers, affected processes, and risk.
4. Update synchronized command surfaces together: triggers, matcher, adapter handler, handle defaults, menu, capability, tests, docs, and i18n.
5. For restart or reconnect flows, register short-lived pending feedback before the API can close the connection.
6. Send post-operation feedback from lifecycle hooks such as `driver.on_bot_connect`.
7. Verify with focused tests, static checks, `nb run -r`, and NapCat debug/log evidence.

## Common Mistakes

- Calling a protocol API only because it appears in old docs or nearby code.
- Forgetting restart can close the WebSocket before immediate feedback returns.
- Adding a menu item without handle defaults, trigger coverage, or capability wiring.
- Treating unit tests as enough when runtime behavior depends on NapCat reconnects.
- Persisting one-shot reconnect feedback into durable config or data files.
