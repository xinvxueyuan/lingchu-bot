# Contributing Guide

> English | [中文](.github/note/CONTRIBUTING-zh.md)

Welcome to Lingchu Bot. The project welcomes code, tests, documentation, bug reports, and feature suggestions. When contributing, keep changes small and clear so maintainers can quickly understand the intent, impact, and verification results.

## Before You Start

- Use Python 3.13.
- Use `uv` to manage Python environments and dependencies.
- Use `pnpm` to manage documentation site and frontend workspace dependencies.
- Use `Taskfile.yml` as the primary local automation entry point.

```bash
task install
```

`task install` runs `uv sync` and `pnpm install`. If you're only working on one side, you can run `uv sync --frozen` or `pnpm install --frozen-lockfile` separately.

Before starting, read [README.md](README.md), [Repository-Policy.md](Repository-Policy.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). When submitting media, screenshots, or sample data, comply with the license and anonymization requirements in the repository policy.

## Local Development Environment Setup

### Prerequisites

- Python 3.13 (managed by `uv`)
- Node.js 22+ and pnpm (for docs site and frontend workspace)
- git

### Step-by-step setup

1. Clone the repository and enter the project directory:

   ```bash
   git clone https://github.com/xinvxueyuan/lingchu-bot.git
   cd lingchu-bot
   ```

2. Install Python dependencies with `uv`:

   ```bash
   uv sync --frozen
   ```

3. Install Node.js dependencies with `pnpm`:

   ```bash
   pnpm install --frozen-lockfile
   ```

4. Or install both at once using the Taskfile:

   ```bash
   task install
   ```

5. Copy `.env.example` to `.env` and adjust values for your environment:

   ```bash
   cp .env.example .env
   ```

6. Install Git hooks (husky):

   ```bash
   pnpm exec husky
   ```

   This is typically auto-installed by `pnpm install`. Verify hooks are active by checking `.husky/` exists.

7. Verify the setup by running checks:

   ```bash
   task check
   task test
   ```

   If both pass, the development environment is ready.

## Toolchain

- `Taskfile.yml`: Unified wrapper for install, check, test, build, fix, version, and i18n workflows.
- `uv`: Python dependencies, virtual environments, Ruff, Pyright, ty, pytest, Babel, and build command entry point.
- `pnpm`: Node workspaces, docs app, Turbo, Gitmoji, Markdown lint, and frontend dependency entry point.
- `turbo`: Orchestrates lint, type check, build, and other tasks for docs and packages.
- `husky`: Installs Git hooks; `pre-commit` runs prek and GitNexus analysis, `commit-msg` validates commit messages, `prepare-commit-msg` attempts to launch Gitmoji interactive mode.
- `prek`: Runs pre-commit hooks via `prek.toml`, checking whitespace, line endings, YAML/TOML/JSON/XML, merge conflicts, large files, private keys, and case conflicts.
- GitNexus / codegraph: Used for code understanding, impact analysis, change scope checking, and safe refactoring.
- Context7: Used for querying current library, framework, SDK, CLI, or cloud service documentation; do not use it as a substitute for business logic analysis or code review.

## Workflow

1. Confirm the problem, success criteria, out-of-scope items, and impact first. If requirements are unclear, add context in an Issue or PR discussion before proceeding.
2. Run `git status --short` before starting to identify existing changes. Do not revert, format, or rewrite files unrelated to the current task.
3. Create a working branch targeting the PR branch; common target branches are `main` or `dev`. Feature/fix branches typically use `feature/`, `fix/`, `hotfix/`, or `releases/` prefixes, as determined by maintainers or the PR page.
4. For larger features, refactors, or behavioral changes, write a plan before implementing. The plan should describe the goal, key changes, test approach, and assumptions.
5. When implementing, prefer following the existing repository structure, tools, and style. Keep the change scope minimal and avoid incidental refactoring.
6. After modifying code, run the necessary checks and state the actual commands and results in the PR.

## Code Intelligence Requirements

Before modifying Python, TypeScript, or shared logic, use GitNexus/codegraph to understand the existing structure. Before modifying a function, class, or method, you must perform an upstream impact analysis and record the direct callers, affected flows, and risk level in the description or PR.

```text
gitnexus_impact({target: "symbolName", direction: "upstream"})
```

- If the impact analysis is `HIGH` or `CRITICAL`, pause and explain the risk before proceeding with changes.
- When exploring unfamiliar code, prefer using GitNexus query/context or codegraph to find execution flows and symbol context.
- Before committing, run GitNexus detect changes to confirm that changes only affect expected symbols and execution flows.
- When renaming symbols, use the graph-tool-supported rename workflow instead of global find-and-replace.
- Docs-only changes can note in the PR that no code symbols were modified; you should still state that you verified related facts using search or the index.

## Development and Verification Commands

Prefer Taskfile high-level tasks:

```bash
task check      # Static checks, format checks, Markdown, lint, type check
task test       # Python tests + docs tests
task build      # Build all workspaces
task ci         # check + test + build
task i18n       # Extract, update and compile gettext catalog
```

When focusing on Python/code changes, you can run directly:

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
uv run -m pyright
uv run -m ty check --output-format github
uv run -m pytest
```

When focusing on docs/frontend changes, you can run directly:

```bash
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs run lint:links
pnpm turbo run build --filter=docs
```

Markdown check:

```bash
pnpm exec markdownlint-cli2
```

When auto-fixing format, prefer running focused commands on relevant files to avoid pulling unrelated files into the PR:

```bash
uv run -m ruff format path/to/file.py
uv run -m ruff check --fix path/to/file.py
```

## Code and Testing Principles

- Use existing repository patterns; do not introduce new frameworks or abstractions for small changes.
- Add tests for user-visible behavior, error branches, edge cases, and async flows.
- When fixing bugs, write a test that reproduces the issue first, then fix the implementation.
- Do not silently swallow unknown exceptions; only catch exceptions you can explicitly handle and provide readable user feedback.
- Comments should explain non-obvious reasons or constraints, not repeat the code itself.
- Documentation changes should be concise and actionable, avoiding inconsistency with CI, Taskfile, or actual directory structure.
- Python code follows Ruff rules (see `pyproject.toml` `[tool.ruff]`). Run `uv run -m ruff check .` and `uv run -m ruff format --check .` before committing.
- TypeScript code follows ESLint rules (see `packages/eslint-config/`). Run `pnpm turbo run lint` before committing.
- Function signatures should have ≤ 5 parameters (Ruff `PLR0913`). Combine related params into a single object if needed.
- Test files must avoid hard-coded module paths; use direct object references instead.
- When migrating files, update all dependent references (tests, i18n, docs, configs) to reflect new paths.

## Commit Convention

Commit messages must conform to gitmoji + Conventional Commits. The first line is enforced by `.husky/commit-msg`. For detailed rules, see [.trae/rules/git-commit-message.md](.trae/rules/git-commit-message.md).

```text
📝 docs: rewrite contributing guide
🐛 fix(mute): fix mute failure feedback
✅ test(database): cover JSON5 store exception branch
```

Run `task gitmoji` for a quick reference. During interactive commits, `.husky/prepare-commit-msg` will attempt to launch `node_modules/.bin/gitmoji --hook` directly (falls back to `npx gitmoji` or a global `gitmoji` install when the local devDep is missing); in non-interactive environments, you can skip the interactive hook but must still ensure the first line format is correct.

## Version Validation System

Lingchu Bot automates version bumps through the CI build workflow. The `versioned-build` job in `👷-ci-builds.yml` derives the bump level and pre-release segment from the **branch name**, so naming the release branch correctly is part of the contribution workflow.

### Branch name conventions

| Branch prefix | `BUMP_LEVEL` | `BUMP_PRERELEASE` | Resulting version semantics |
| --- | --- | --- | --- |
| `dev-major-*` | `major` | (see pre-release column) | Breaking version bump, e.g. `1.0.0` |
| `dev-minor-*` | `minor` | (see pre-release column) | Feature bump, e.g. `0.1.0` |
| any other `dev-*` | `patch` | (see pre-release column) | Patch bump, e.g. `0.0.2` |

The pre-release segment is derived independently:

| Branch prefix | `BUMP_PRERELEASE` | Example tag |
| --- | --- | --- |
| `dev-alpha-*` | `alpha` | `0.1.0a1` |
| `dev-beta-*` | `beta` | `0.1.0b1` |
| `dev-rc-*` | `rc` | `0.1.0rc1` |
| `dev-stable-*` | `stable` (clears the pre-release segment) | `0.1.0` |
| any other `dev-*` | `dev` | `0.1.0.dev1` |

### Validation tasks

Version changes run through three guarded tasks defined in `Taskfile.yml`:

- `task ci:version:bump` — accepts `BUMP_LEVEL` (default `patch`) and `BUMP_PRERELEASE` (default `dev`). It handles stable vs. pre-release tags intelligently: stable labels require both a level and a pre-release segment, same-class pre-release labels only bump the pre-release counter, and `stable` clears the pre-release segment.
- `task ci:version:precheck` — runs before the version is written. It validates PEP 440 compliance, ensures the candidate version is greater than every existing tag, checks source-file consistency (advisory), and rejects duplicate tags.
- `task ci:version:postcheck` — runs after `ci:version:write-config`. It calls `release:verify-version` and validates dev-release semantics so a broken version never reaches the build artifacts.

When you open a release PR, name the branch with the prefix that matches the intended bump and pre-release semantics above. CI does the rest; do not hand-edit `core/config.py` or `package.json` versions on a release branch.

## Pull Request Requirements

PR descriptions should include:

- Purpose of the change and user-visible effects.
- Key implementation points, especially public interfaces, command behavior, configuration, data structure, or compatibility changes.
- GitNexus/codegraph impact analysis results; for docs-only changes, note that no code symbols were modified.
- Check commands that were run and their results.
- Associated Issues, e.g., `Closes #123`.
- Any outstanding items, known risks, or trade-offs that need maintainer confirmation.

### PR naming conventions

- Use the format `<type>(<scope>): <subject>` in the PR title, matching the commit message style (without the gitmoji prefix).
- Keep PR titles under 50 characters.
- Use lowercase scope names: `auth`, `db`, `api`, `i18n`, `docs`, `frontend`, `core`, `handle`, `platforms`, `permissions`, `repositories`, `services`, `tests`.
- Link the PR to the related issue using `Closes #123` or `Fixes #123` in the PR description.
- For breaking changes, add `!` after the type/scope and describe the breaking change in the PR body.

### PR checklist

Before requesting review, confirm each item:

- Commits carry a `Signed-off-by:` trailer (Developer Certificate of Origin 1.1, see <https://developercertificate.org/>). The `.husky/commit-msg` flow auto-appends it; verify it is present if you amend or rebase.
- User-visible behavior, configuration, or compatibility changes have a matching `CHANGELOG.md` entry under `## [Unreleased]`.
- Code changes include a GitNexus impact analysis result (or a note that no code symbols were modified).
- The relevant checks from the quick verification matrix were run and pass.
- Release PRs (branch `releases/**`) additionally confirm: the version was written by `task ci:version:write-config`, `ci:version:precheck` and `ci:version:postcheck` both pass, and the build artifacts carry SLSA Build L3 provenance (see [SECURITY.md](SECURITY.md) for the `gh attestation verify` command).

## CI and Failure Handling

- PRs trigger GitHub Actions; pushes to `main` and `dev` also trigger main CI.
- `🧪 Python CI` runs Static Analysis (`task ci:static`) and Tests & Type Check (Pyright, ty, pytest across the multi-database matrix); `🧪 Frontend CI` runs Docs Check (Turbo lint, type check, link validation, docs test).
- `👷 CI-builds` runs `task ci:build`; on pushes to `main`, `dev`, `releases/**`, it also performs version writing, build artifact archiving, provenance attestation, and tag workflow.
- `📚 Docs Deploy` runs pnpm/turbo lint, docs test, and docs build when docs-related paths are pushed to `main` or `dev`, then deploys to GitHub Pages.
- The auto-format job in `🧪 Python CI` on pushes to `main` and `dev` runs `task ci:fix` and may auto-commit format fixes.

If CI fails, open the failed job's logs first and locate the specific command, rule, and line number. When fixing CI, only change the minimal scope that caused the failure, and re-run the corresponding local command to verify.

## Release Process

Formal releases use `releases/<version>` branches.

1. Run `task release:prepare VERSION=0.0.1`.
2. Update `CHANGELOG.md`, `.github/releases/0.0.1.md`, README status text, and policy records.
3. Run `task check && task test && task ci:build && task smoke`.
4. Push with `task release:publish VERSION=0.0.1`.
5. Verify PyPI, GHCR, and GitHub Release artifacts.

The release workflow runs `scripts/clean-release-infra.sh` before building artifacts so agent, CI, and local workspace infrastructure is not copied into distribution outputs.
GitHub Release body text comes from `.github/releases/<version>.md`; keep that file reviewed with the changelog before pushing a release branch.

Publishing uses short-lived, OIDC-based credentials — no long-lived package tokens are stored in the repository:

- **PyPI** publishes through Trusted Publishing / OIDC. The PyPI project is configured to trust this repository's `🚀-release.yml` workflow on the `releases/**` branch ref.
- **GHCR** (`ghcr.io/xinvxueyuan/lingchu-bot`) pushes with the ephemeral `GITHUB_TOKEN` scoped to `packages: write`.
- Build artifacts (`dist/*`) are attested with SLSA Build L3 provenance via `actions/attest-build-provenance@v4.1.0`. See [SECURITY.md](SECURITY.md) for the `gh attestation verify` command consumers can run.

## Code Review Process

1. **Self-review**: Before requesting review, re-read your diff and verify that every change is intentional.
2. **Automated checks**: CI must pass. If a check fails, fix the root cause rather than suppressing the warning.
3. **Reviewer assignment**: Maintainers assign reviewers based on the changed areas. At least one approval is required.
4. **Review criteria**:
   - Changes are minimal and focused on the stated goal.
   - Tests cover new behavior, error branches, and edge cases.
   - No unrelated refactoring or formatting changes.
   - Public interfaces, configuration, and data structure changes are documented.
   - GitNexus impact analysis is included for code changes.
5. **Addressing feedback**: Respond to every comment. Push fixes as new commits (do not force-push during review unless requested).
6. **Merge**: A maintainer merges the PR after approval and CI passes. Squash-merge is the default strategy.

## Issues and Communication

When reporting issues, please provide:

- A brief title.
- Steps to reproduce.
- Expected and actual results.
- Environment information, such as OS, Python version, adapter, or command input.
- Relevant logs, screenshots, or minimal reproduction examples.

For feature requests, describe the use case, expected behavior, and acceptable trade-offs. For security issues, refer to [SECURITY.md](SECURITY.md).

## License and Code of Conduct

The Project uses a **phased open-source license stack** described in
[Repository-Policy.md](Repository-Policy.md). The current phase covers
LGPL-3.0-or-later (code), FDL-1.3-or-later (documentation), and CC0-1.0
(visual elements); the future phase — triggered automatically on the
earlier of one year after the first public release or the first major
version bump — covers MIT-or-later or Apache-2.0-or-later (code) and
CC-BY-SA-4.0-or-later (documentation and visual elements). The transition only applies to
contributions submitted on or after the trigger date.

By submitting a contribution, you accept the terms of
[CLA.md](CLA.md), which grants the Project the rights it needs to
execute the transition described above.

When participating in discussions and reviews, follow
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Being specific, respectful,
and verifiable is the best way to keep collaboration smooth.
