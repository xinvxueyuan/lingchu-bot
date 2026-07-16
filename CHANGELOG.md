<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Fixed

### Security

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

[Unreleased]: https://github.com/xinvxueyuan/lingchu-bot/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.0.1
