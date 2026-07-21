# Runtime Handle Defaults Specification

## Status

Implementation specification for PR #15 follow-up.

## Problem

Handle TOML files declare runtime defaults, but the capability is incomplete:

- `member_mute.defaults.mute_duration` is written by PR #15 but is not consumed
  when the duration argument is omitted.
- Several declared defaults are unused or are shadowed by parser literals.
- There is no safe, discoverable runtime interface that can update defaults for
  every handle that declares them.
- PR #15 does not propagate its user-visible command to i18n or QQ command
  reference documentation.

## Goals

1. A command operator can list and update every registered handle default at
   runtime without editing localstore TOML files manually.
2. The update is schema-validated, persisted through `HandleConfigManager`,
   recorded in command audit, and takes effect in the same process.
3. Each non-empty default currently declared by a handle is either consumed by
   its business handler or removed as dead configuration. Parser literals must
   not override a handle default.
4. Existing dedicated `set_default_mute_duration` remains a compatible,
   user-friendly shortcut and delegates to the same default-update boundary.
5. Menu, permission, trigger, i18n, docs, and tests describe the new behavior.

## Non-goals

- Editing `enabled` or `policies` through the default-value command.
- Inventing default fields for handles that currently declare an empty
  `defaults` object.
- Supporting arbitrary JSON/TOML paths or untyped values from chat input.

## Domain Model

`HandleDefaultDefinition` is the authoritative registry entry for one mutable
default field. It contains:

- `command_key` and `field` identifying the registered handle configuration;
- a localized display name for the handle and field;
- a parser/validator that accepts only the field's supported runtime input;
- optional formatting for the value in user feedback.

The registry must cover all currently declared fields:

| Handle | Field | Runtime behavior |
| --- | --- | --- |
| `member_mute` | `mute_duration`, `default_reason` | Missing duration/reason uses config |
| `remote_mute` | `mute_duration`, `default_reason` | Missing duration/reason uses config |
| `block_member` | `block_duration`, `default_reason` | Missing duration/reason uses config |
| `remote_block` | `block_duration`, `default_reason` | Missing duration/reason uses config |
| `recall_message` | `default_count` | Missing count uses config |
| `protect_member` | `whitelist_scope` | Existing config consumption retained |
| `kick_member` | `require_reason`, `audit_level` | Existing behavior must consume both fields |

Nullable duration fields accept the explicit literal `permanent` (Chinese
alias: `永久`) and persist `null`; positive duration fields remain bounded by
the OneBot 30-day limit. `whitelist_scope` only accepts `group` or `global`;
booleans only accept locale-independent `true`/`false` plus Chinese aliases.

## Command Interface

New OneBot V11 management commands:

```text
查看功能默认值 [功能]
list-handle-defaults [handle]

设置功能默认值 <功能> <字段> <值>
set-handle-default <handle> <field> <value>
```

The commands use the standard selected-adapter permission, state gate, silent
mode, menu, and audit pathways. They are available only for a configured
runtime identity that has the `manage_handle_defaults` permission key. Unknown
handles, unsupported fields, malformed values, and failed persistence produce
localized failures and do not alter cache or disk.

Dedicated `设置默认禁言 <秒数>` / `set-default-mute <seconds>` remains and
updates `member_mute.mute_duration` through the same service.

## Implementation Slices

1. Add a typed default-definition registry and a service that lists, parses,
   validates, and persists one field while preserving sibling defaults.
2. Make local mute and remote mute consume config defaults if their optional
   duration/reason arguments are omitted; remove the remote parser's hard-coded
   `60` fallback.
3. Make remote block consume its own config defaults. Make kick enforce
   `require_reason` and include `audit_level` in its audit payload only if the
   existing audit model supports it; otherwise remove `audit_level` from the
   defaults registry as dead configuration.
4. Add the management command, OneBot handler, menu feature, trigger catalog,
   permission wiring, and shortcut delegation.
5. Add localized messages, bilingual QQ command-reference documentation, and
   behavioral tests at command/handler seams.

## Acceptance Criteria

- Updating `member_mute.mute_duration` followed by `mute @user` calls
  `set_group_ban` with the updated value.
- Updating `remote_mute.mute_duration` followed by `remote-mute <group> @user`
  calls `set_group_ban` with the updated value.
- `list-handle-defaults` exposes every non-empty registered `defaults` field;
  `set-handle-default` rejects an unknown handle/field and invalid value.
- Existing unrelated default fields survive a partial update.
- Writes appear in `<command_key>.toml`, refresh `HandleConfigManager` cache,
  and audit records identify `manage_handle_defaults` or the shortcut action.
- Chinese and English trigger locales do not register cross-locale aliases.
- Targeted pytest, Ruff, Pyright, ty, `task i18n`, documentation lint, and a
  short startup smoke test pass before handoff.

## Risks and Decisions

- A generic untyped config writer would expose arbitrary configuration mutation
  through chat. The typed registry deliberately restricts the surface.
- Separate per-field commands would grow linearly and create duplicate parsing,
  validation, menu, permission, and documentation paths. One generic command
  plus the mute shortcut is the smallest durable interface.
- Default updates are process-wide plugin configuration, not group-scoped;
  feedback and docs must state that scope explicitly.
