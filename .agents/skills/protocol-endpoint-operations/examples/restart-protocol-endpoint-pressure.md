# Restart Protocol Endpoint Pressure Scenario

An agent is asked to add `重启协议端 [平台]` to Lingchu Bot.

Failure signs without the skill:

- Adds only a handler and forgets triggers, matcher registration, adapter handler wiring, handle defaults, menu, capability, tests, docs, or i18n.
- Calls a protocol API because it appears plausible, without live NapCat or OneBot debug/log evidence.
- Sends only immediate command feedback and forgets reconnect feedback after restart.
- Registers pending reconnect feedback after the restart API, letting the connection close before the feedback request is saved.
- Stores one-shot pending feedback in a persistent runtime file instead of short-lived process memory.
- Runs only unit tests and skips focused static checks, `nb run -r`, and NapCat debug/log verification.

Passing behavior with the skill:

- Checks `git status --short`, preserves unrelated worktree changes, and runs GitNexus impact analysis before symbol edits.
- Adds synchronized command surfaces: triggers, matcher, adapter handler, handle defaults, menu, capability, tests, docs, and i18n.
- Registers pending reconnect feedback before the restart can sever the connection.
- Uses a lifecycle hook such as `driver.on_bot_connect` to send the post-restart message.
- Verifies with focused tests, static checks, `nb run -r`, and NapCat debug/log evidence from one live marker command.
