---
icon: lucide/check-circle
title: Testing and CI
---

## Testing and CI

CI runs through GitHub Actions and mainly covers static checks, type checks, tests, and documentation deployment.

## Static checks

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
```

## Type checks

```bash
uv run -m pyright .
uv run -m ty check --output-format github
```

## Tests

```bash
uv run -m pytest
```

If only one module changed, run the related test file first, then broaden the scope as needed.

## Markdown checks

```bash
npx markdownlint-cli2 "docs/**/*.md" "README.md" "CHANGELOG.md" "CONTRIBUTING.md" "CODE_OF_CONDUCT.md" ".github/**/*.md"
```

## Documentation build

The documentation deployment workflow uses:

```bash
uvx zensical build --clean
uvx zensical build --config-file zensical.en.toml --clean
```

After changing `zensical.toml` or `docs/`, run the same command locally to confirm that the site builds.

## Internationalization checks

After changing translatable strings, run:

```bash
task i18n:extract
task i18n:update
task i18n:compile
```

If you only change documentation that describes i18n, gettext catalogs do not need to be regenerated.

## Handling CI failures

Open the failing job logs and locate the command, rule, and line number. Fix only the smallest related scope and rerun the corresponding local command.
