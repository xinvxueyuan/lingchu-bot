# ADR-0002: Single source of truth for adapter→module-path mapping

- **Status**: Accepted
- **Date**: 2026-07-28
- **Decider**: architecture review (`.trae/specs/prepare-0.2.0-release/architecture-review.md`) → `consolidate-adapter-module-registry` spec
- **Supersedes**: none
- **Note**: ADR-0001 (command definition ownership), ADR-0003 (migration compat-type
  enforcement), ADR-0004 (schema generation ownership) remain candidates in the
  architecture review and are not yet recorded. This is the first formally
  recorded ADR; the number matches the candidate label for traceability.

## Context

Before this decision, the adapter→handler-module mapping was owned by three
places, and one of them was wrong:

1. `handle/qq/adapters/__init__.py::_ADAPTER_MODULES` — per-loader relative
   paths for group command handlers.
2. `handle/menu.py::_ADAPTER_MODULES` — per-loader relative paths for menu page
   handlers.
3. `platforms/registry.py::_PROTOCOL_IMPLEMENTATIONS` — absolute `module_path`
   values used for database seeding.

The Telegram command entry in (1) used a two-dot relative path that resolved to
a 5-line compatibility shim (`handle/qq/adapters/telegram/default/__init__.py`)
instead of the real module at `handle.telegram.adapters.default`. So the
registry's `module_path` for Telegram drifted from the path the loader actually
imported. Adding an adapter meant editing three dicts and hoping they agreed —
a classic shallow-module smell: three near-identical interfaces to one fact.

This was documented as findings P1-3, P1-4, and P1-5 in the 0.2.0 architecture
review, and flagged as "ADR-002 candidate" with two options:

- **Option A**: Registry owns module paths; loaders consume
  `get_protocol_implementations(adapter_id)` and import by `module_path` —
  single source of truth, but couples the registry to import-time module paths.
- **Option B**: Keep per-loader dicts but generate them from the registry at
  import time — preserves loader isolation, but adds a generation step and the
  dicts can still drift if the generator is bypassed.

## Decision

**Accept Option A.** `platforms/registry.py::_PROTOCOL_IMPLEMENTATIONS` is the
single source of truth for adapter→module-path mapping. The handler loader in
`handle/qq/adapters/__init__.py` consumes `get_protocol_implementations` and
imports absolute module paths via `import_module(module_path)` — no
`adapter_modules` dict, no relative-import `package` argument, no compatibility
shim.

Concretely:

- `load_adapter_handlers(adapter_id, kind)` derives module paths from the
  registry. Command-handler modules = every implementation `module_path` for
  the adapter; menu-page modules = the default-protocol implementation's
  `module_path` + `.menu`. Results are cached under `f"{kind}:{adapter_id}"`.
- `import_handle(kind: HandlerKind)` is the single entry point, dispatching
  `"command"` and `"menu"`. The two former entry points
  (`handle/qq/adapters::import_handle` and `handle/menu::import_handle`)
  collapse into one.
- `handle/qq/adapters/__init__.py::_ADAPTER_MODULES` and
  `handle/menu.py::_ADAPTER_MODULES` are deleted.
- The compatibility shim `handle/qq/adapters/telegram/default/__init__.py` is
  deleted; the loader imports `handle.telegram.adapters.default` directly.

## Consequences

**Positive:**

- One source of truth: database seeding and handler loading read the same
  `module_path` by construction — no second dict can diverge (P1-3 resolved).
- The Telegram metadata/loaded path divergence disappears (P1-5 resolved); the
  shim is unreachable and deleted (P1-4 resolved).
- Adding an adapter now means one edit (`_PROTOCOL_IMPLEMENTATIONS`) instead of
  three. The deletion test passes: removing the per-loader dicts concentrates
  complexity into the registry rather than just moving it.
- The loader deepens from a shallow `(adapter_id, adapter_modules, package)`
  interface to a deeper `(adapter_id, kind)` interface — the caller no longer
  supplies the mapping it expects the loader to use.
- Tests improve: the loader's test surface is now `(adapter_id, kind) →
  modules`, which is what callers actually depend on, rather than the internal
  dict shape.

**Negative:**

- The registry is now coupled to import-time module paths: a `module_path`
  rename requires updating `_PROTOCOL_IMPLEMENTATIONS` and will fail loudly at
  startup (`ModuleNotFoundError`) rather than silently. This is acceptable —
  loud failure is preferable to silent drift.
- `HandlerKind` (`"command" | "menu"`) is a new dispatch dimension. It is
  recorded in `CONTEXT.md` under "Handler Loading" so future work speaks the
  same term.

## Alternatives considered

- **Option B** (generate per-loader dicts from the registry): rejected. It
  preserves the shallow interface and adds a generation step; the dicts can
  still drift if someone bypasses the generator, and the shim survives. The
  deletion test fails: removing the generator just moves complexity, it does
  not concentrate it.
- **Status quo** (three dicts): rejected. The Telegram divergence was already
  a live bug masked by the shim; adding a fourth adapter would compound the
  drift surface.

## References

- Architecture review: `.trae/specs/prepare-0.2.0-release/architecture-review.md`
  (findings P1-3, P1-4, P1-5; ADR-002 candidate)
- Implementing spec: `.trae/specs/consolidate-adapter-module-registry/spec.md`
- Domain term: `CONTEXT.md` → "Handler Loading" → "Handler Kind"
