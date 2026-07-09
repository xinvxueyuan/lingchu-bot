# Handle Feature Workflow

Use this when adding, changing, deleting, or refactoring a Lingchu `handle`
command, QQ matcher, adapter handler, menu entry, command trigger, or
`command_key`.

## Core Rule

GitNexus, static search, tests, and old skills are useful but incomplete. Do
not treat "the tool did not report it" as "there is no impact". If tool output
is stale, noisy, or does not match the current file structure, refresh the
index when appropriate and then manually inspect the known coupling points
below.

Prefer backward-compatible behavior for runtime config, JSON5 files, persisted
data, command keys, menu config, and documented command behavior. When a
breaking change is intentional, document the migration path and update tests
that prove old unsupported shapes fail clearly or are migrated safely.

## Feature Checklist

1. Map the command load path.
   - Shared matchers and triggers live in `handle/qq/commands/*.py`.
   - OneBot V11 handlers live under `handle/qq/adapters/onebot11/default/` and
     implementation overrides such as `handle/qq/adapters/onebot11/napcat/`.
   - Startup calls `group_import_handle()` and `menu_import_handle()` from
     `start/startup.py`.
   - Adapter packages register handlers through top-level imports in
     `handle/qq/adapters/onebot11/default/__init__.py` and related
     implementation `__init__.py` files. A new handler file that is not imported
     will not register.

2. Keep `command_key` stable and wired end to end.
   - `selected_adapter_handle()` stores the `command_key` on the matcher and
     wraps adapter, permission, gate, and silent-mode checks.
   - A business command without `command_key` bypasses command permission checks
     and will not align with menu authorization.
   - The same key must match triggers, menu features, permission grants, menu
     JSON references, and protected-subject feature settings.

3. Sync command triggers and locale behavior.
   - Add new commands to `_DEFAULT_COMMAND_TRIGGERS`.
   - Do not register Chinese and English trigger aliases together; trigger
     language is selected by configured locale.
   - Check runtime trigger overrides and duplicate-trigger validation.

4. Sync menu, capability, and permission visibility.
   - Update `handle/menu.py` feature rows, usage text, summary, capability, and
     availability rules.
   - Confirm menu rendering hides unsupported platform, adapter,
     implementation, version, and unauthorized command entries.
   - `menu.json5` may customize display text and order, but code still owns
     runtime capability and availability. Unknown `command_key` entries should
     remain invalid.
   - SUPERUSER and menu authorization bootstrap uses `MENU_FEATURES.command_key`;
     verify permission tests when command keys change.

5. Sync gate and silent-mode behavior.
   - Default handlers check handle gate first, then silent mode.
   - `handle_active` resolves as global AND platform.
   - `silent_mode` resolves as global OR platform.
   - Recovery commands must preserve bypass behavior: boot/shutdown bypass gate
     and silent mode; silence/speak bypass silent mode only.

6. Sync runtime config, JSON5, schemas, and persisted data.
   - If behavior becomes configurable, update `RuntimeConfig`, default JSON5
     payloads, schema text in `core/schemas.py`, generation/install tests, and
     configuration docs.
   - If the handler uses `bot_state.json5`, `menu.json5`, or localstore data,
     test both default creation and existing-file compatibility.
   - Runtime paths must stay owned by `nonebot_plugin_localstore`.

7. Sync SQL and repository side effects.
   - Audit message store, blocklist, subject policy, permission grants, and
     registry repositories if the handler records, enforces, or mutates state.
   - Add or update repository/database tests for new persisted behavior.
   - Preserve compatibility for already-stored data when live debugging proves
     old rows exist.

8. Sync user-visible text and docs.
   - User-visible `await _("...")` strings require `task i18n` and inspection of
     changed PO entries.
   - `LocalizedText(zh, en)` menu text is not gettext, but it is still
     user-visible and needs docs/test review.
   - Check QQ command reference docs, user command guide, platform
     implementation docs, and configuration docs.

9. Keep package boundaries clean.
   - Runtime/package code and resources that must be built or distributed belong
     under `src/plugins/nonebot_plugin_lingchu_bot/`.
   - Repository-root `config/`, `data/`, and generated runtime files are
     disposable development artifacts unless explicitly documented otherwise.

## Other Business Changes

Use the same coupling checks for non-feature work that touches command behavior:

- Refactor or move handlers: preserve import registration, matcher identity,
  `command_key`, permission behavior, menu visibility, and test module coverage.
- Rename command keys or triggers: treat this as a compatibility-sensitive
  migration. Check runtime overrides, `menu.json5`, permission grants,
  protected-subject feature keys, docs, and user examples before accepting the
  new name.
- Delete commands or capabilities: remove handler imports, triggers, menu rows,
  permission grants/seeds, config defaults, schema references, tests, docs, and
  stale i18n strings together. Existing persisted config should fail with a
  clear error or be migrated intentionally.
- Change JSON5 or SQL shape: keep localstore path ownership, add migration or
  compatibility reads for existing files/rows, update schemas/defaults/docs, and
  add tests for old and new shapes.
- Change adapter boundaries or external APIs: verify current upstream docs/API
  surfaces first, then test the adapter-specific behavior and fallback paths.

## Runtime Bug Workflow

For `fix: handle not work`, load `interactive-runtime-debugging` first. Use
`nb run -r`, NapCat logs/debug WebSocket when available, a unique marker command,
and concrete DB/API/UI evidence to prove the failing layer before editing.

After the fix and regression test, return to the feature checklist above so the
runtime fix does not drift from menus, permissions, config, i18n, docs, or
packaging rules.

## Focused Validation

- Python handle/config minimum:
  `uv run -m pytest tests/handle/commands/ tests/core/test_runtime_config.py tests/core/test_bot_state.py tests/core/test_menu_config.py tests/core/test_schemas.py tests/test_i18n.py`
- SQL/repository changes:
  `uv run -m pytest tests/repositories/ tests/database/ tests/permissions/`
- Static checks for Python changes:
  `uv run -m ruff check . --output-format=github`
  `uv run -m ruff format --check .`
  `uv run -m pyright`
  `uv run -m ty check --output-format github`
- i18n string changes: `task i18n`
- Docs changes:
  `pnpm --filter docs lint`
  `pnpm --filter docs test`
  `pnpm turbo run check-types --filter=docs`
  `pnpm --filter docs lint:links`

Use narrower checks during iteration when the touched surface is smaller, but
expand verification when the command crosses adapter, permission, persistence,
or user-facing documentation boundaries.
