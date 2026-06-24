---
name: interactive-runtime-debugging
description: Use when a Lingchu Bot runtime feature fails only in live use, especially with NapCat, OneBot, QQ UI accounts, WebSocket debug pages, database-backed handlers, or user complaints about guessing instead of real reproduction.
---

# Interactive Runtime Debugging

## Core Rule

Prove the failing layer with live evidence before editing. Do not treat code
inspection as proof when the user provided runtime tools, browser connectors,
or logged-in app accounts.

## Workflow

1. Start or attach to the runtime first.
   - For Lingchu, prefer `nb run -r` and keep the terminal session open.
   - Wait for adapter/plugin load and the OneBot/NapCat connection line.
   - Record exact bot id, group id, user id, message id, API names, and replies.

2. Connect the live debug surfaces.
   - Open NapCat real-time debug/log pages when available:
     `http://127.0.0.1:6099/webui/debug/ws` and
     `http://127.0.0.1:6099/webui/logs`.
   - If the requested browser connector times out, say so briefly and switch to
     an available browser/computer connector instead of dropping live debugging.
   - Prefer page state, screenshots, console logs, and WebSocket events over
     assumptions.

3. Reproduce with real actors.
   - Use the requested logged-in app windows when the bug depends on identity,
     permissions, or UI state.
   - Identify each window by visible role/account evidence before typing.
   - Send unique marker text so logs, DB rows, and UI state can be correlated.
   - For destructive tests, keep the action narrow: one test message, one command.

4. Trace the cross-boundary data path.
   - UI event -> bot console event -> handler match -> database query -> adapter
     API call -> NapCat result -> UI outcome.
   - At each boundary, capture the concrete input and output. Missing evidence at
     a boundary is the next debugging target.
   - If a handler reports "skipped" or "0 changed", inspect the candidates it
     actually used, not just the intended query.

5. Inspect persisted state when the feature is database-backed.
   - Locate the active runtime DB, not a historical or ignored file.
   - Query recent rows around the marker text and compare stored identity fields
     against handler filters.
   - Treat mismatched identity dimensions as root-cause candidates only after
     live logs show the same mismatch affects behavior.

6. Edit only after root cause is evidenced.
   - Run project-required impact analysis before modifying symbols.
   - Fix the source of future data and add compatibility for already-stored data
     when live state proves old rows exist.
   - Add a focused regression test for the bad stored/runtime shape.

7. Verify with both automated and live checks.
   - Run narrow unit/static checks that cover the changed code.
   - Hot reload or restart the runtime and wait for reconnection.
   - Repeat the real UI scenario with a fresh marker and confirm the intended API
     call appears in logs and the UI outcome changes.
   - Stop long-running debug processes before finalizing.

## Evidence Checklist

Use this checklist before claiming completion:

| Requirement | Strong evidence |
| --- | --- |
| Runtime is connected | `nb run -r` log shows adapter loaded and bot connected |
| User action reproduced | QQ/browser screenshot or DOM text shows test marker/command |
| Handler matched | console shows matcher/command parse for the command |
| API path reached | console/NapCat shows relevant `get_msg`, `delete_msg`, etc. |
| Stored state is correct | DB row for marker has expected bot/group/user/message ids |
| Fix works live | UI shows the real outcome and marker is gone/changed |
| Regression covered | focused tests fail without the fix and pass with it |

## Common Mistakes

- Using code inspection as a substitute for the provided runtime tools.
- Testing with the wrong logged-in account/window because two app windows share a
  title.
- Assuming `get_session_id()` is a group identifier. For OneBot V11 group
  messages it can include both group and user ids; group-scoped history features
  should store/query by `group_id`.
- Querying a repository-local DB while the running bot uses localstore/ORM data
  elsewhere.
- Declaring success after a unit test when the bug originally appeared only
  through NapCat or QQ UI.
