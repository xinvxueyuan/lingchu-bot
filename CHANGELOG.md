<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.1.0] - 2026-07-27

First minor release. The jump from `0.0.1` to `0.1.0` reflects significant
accumulated changes: TOML configuration migration, multi-database support,
LLM service integration, docs site, CLI tooling, and smoke test enhancement.

### Added

- Docs site home hero: full-bleed p5.js "Organic Turbulence" flow-field
  sketch with layered Perlin noise, steered particles, accumulating trails,
  velocity-mapped color, and `prefers-reduced-motion` support.
- Dependency-free shadcn-style `Badge` and `Alert` components for the docs
  site, reading Starlight theme tokens and adapting to light/dark mode.
- Global style polish for the docs site: accent-tinted selection color,
  refined theme-aware scrollbars, hero banner layout, card hover glow,
  feature grid, and inline code/block refinement.
- Three-stage runtime smoke test flow (dev env / prod env clean-localstore /
  CLI tool verification) documented across `AGENTS.md`, `CLAUDE.md`,
  `.github/note/AGENTS-zh.md`, and both EN/zh `testing-ci.mdx` pages.
- Non-Docker prod-env smoke test job (`smoke-test-prod-env`) in
  `👷-ci-builds.yml`, validating schema-write-free startup on a pristine
  runner without Docker-specific defaults.
- `lingchu config init` now seeds `llm.toml` from `LINGCHU_AI_*` environment
  variables, enabling zero-touch LLM profile bootstrap in containerized and
  CI environments.

### Changed

- **Breaking:** replaced all Lingchu-owned JSON5 configuration and state files
  with TOML backed by `rtoml`. Legacy `.json5` files are not read, migrated, or
  backed up; recreate configuration as `.toml`. Optional `None` values are
  represented by omitted keys, and programmatic writes do not preserve custom
  comments or formatting.
- Refreshed governance and documentation infrastructure: realigned
  `AGENTS.md`, `CLAUDE.md`, and `.github/note/AGENTS-zh.md` under the CREATE
  framework; corrected README environment variable tables (added `LINGCHU_`
  prefix) and pinned Python 3.13 / Node.js 24+ requirements; completed the CI
  workflow list and husky pre-commit description in `CONTRIBUTING.md`; expanded
  the PR template checklist; exposed the orphan `user-guide/deployment/tipo-llama-cpp`
  page and added 7 bilingual architecture doc pairs
  (permissions, i18n-runtime, storage-orm, llm-service, scheduler,
  platform-registry, api-audit) under `apps/docs`.

### Deprecated

### Removed

- Removed legacy `.serena/` tool configuration directory (cleanup of a
  deprecated tool's残留).

### Fixed

- Corrected project brand name from "灵枢" to "灵初" across docs site
  (hero eyebrow, sketch concept, integration guide).
- Fixed hero p5.js animation layout: Astro `client:load` wraps the island
  in `<astro-island>`, breaking the `>` child selector; the canvas now
  correctly overlays behind the hero content instead of sitting side-by-side.
- Fixed quick-navigation cards being non-clickable: Starlight `Card` component
  does not support `href`; cards are now wrapped in `<a>` tags for navigation.
- Fixed `_LLMConfigError` on `nb run` startup when `llm.toml` is missing or
  empty: `ensure_llm_config_file_async()` no longer creates the file at
  startup; `load_llm_runtime_config()` falls through to an empty mapping and
  emits an actionable warning instead of a traceback.
- Fixed Windows ESLint failure caused by `brace-expansion@5.x` (ESM-only)
  being forced onto `minimatch@9.0.9` (expects CJS default export); added a
  targeted `minimatch@9.0.9>brace-expansion` override to `^2.1.2` (not
  affected by CVE-2026-14257) while keeping the global `^5.0.8` security fix.

### Security

- `brace-expansion` overridden to `^5.0.8` globally to mitigate
  CVE-2026-14257 / GHSA-mh99-v99m-4gvg (DoS via memory exhaustion).

### Release Notes

- Software code remains under `LGPL-3.0-or-later`.
- Documentation remains under `GFDL-1.3-or-later`.
- Visual elements remain under `CC0-1.0`.

## [0.0.1] - 2026-07-06

Initial formal release for QQ group management through OneBot V11.

### Added

- QQ group management commands for member moderation, speech management, group operations, remote management, bot control, and dynamic menus.
- Runtime permission, protection, i18n, message storage, and API audit support.
- Docker runtime support and documentation site.
- Multi-database test coverage across SQLite, PostgreSQL, MySQL, MariaDB, Oracle, and SQL Server.

### Release Notes

- Software code remains under `LGPL-3.0-or-later`.
- Documentation remains under `GFDL-1.3-or-later`.
- Visual elements remain under `CC0-1.0`.

[Unreleased]: https://github.com/xinvxueyuan/lingchu-bot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.1.0
[0.0.1]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.0.1
