# Pull Request

> 提交前请阅读 [CONTRIBUTING.md](../CONTRIBUTING.md) 与
> [Repository-Policy.md](../Repository-Policy.md)；中文模板见
> [.github/note/PULL_REQUEST_TEMPLATE-zh.md](note/PULL_REQUEST_TEMPLATE-zh.md)。

Thanks for taking the time to contribute to Lingchu Bot! Please fill in
the sections below so reviewers can quickly understand intent, impact,
and verification.

## Summary

<!-- 1-3 sentences: what this PR does and why. -->

## Related Issues

<!-- Link related issues: Closes #123, Fixes #456, Refs #789. -->

## Type of Change

<!-- Put an `x` in the box that applies. -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing
      functionality to change)
- [ ] Documentation update
- [ ] Refactor / cleanup
- [ ] Build / CI / tooling
- [ ] Tests only

## Pre-Submit Checklist

<!-- Put an `x` in each box once you have confirmed the item. -->

- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md) and
      [CLA.md](../CLA.md).
- [ ] I agree to the terms of [CLA.md](../CLA.md); this contribution
      may be relicensed as part of the phased license stack described
      in [Repository-Policy.md](../Repository-Policy.md).
- [ ] My commits carry a `Signed-off-by:` line (DCO 1.1) — use
      `git commit -s` or append `Signed-off-by: Name <email>` manually.
- [ ] For user-facing or behavior changes, I have added a
      `CHANGELOG.md` entry under `## [Unreleased]` in the appropriate
      subsection (Added / Changed / Deprecated / Removed / Fixed /
      Security).
- [ ] For code changes, I ran `gitnexus_impact` (or the equivalent
      analysis) and recorded the blast radius below.
- [ ] For code changes, I have run `uv run -m ruff check .`,
      `uv run -m ruff format --check .`, `uv run -m pyright`,
      `uv run -m ty check .`, and `uv run -m pytest` locally.
- [ ] For docs site changes, I have run `pnpm --filter docs lint`,
      `pnpm --filter docs test`, and
      `pnpm turbo run build --filter=docs` locally.
- [ ] For Markdown changes, I have run
      `pnpm exec markdownlint-cli2` locally.
- [ ] I have added or updated tests covering the change.
- [ ] I have updated relevant documentation, i18n strings
      (`task i18n`), runtime config, and handle defaults as needed.
- [ ] I have run `prek run --all-files` (or relied on the
      `pre-commit` hook) and confirmed all files carry SPDX license
      declarations (REUSE compliance).
- [ ] For changes to `AGENTS.md`, `CLAUDE.md`, or
      `.github/note/AGENTS-zh.md`, I have kept the three mirror files
      structurally aligned (excluding GitNexus marker blocks).

### Release PR Checklist (only for `releases/**` branches)

<!-- If this PR targets a `releases/<version>` branch, confirm the
supply chain attestation flow. Otherwise delete this subsection. -->

- [ ] Version bump was driven by a `dev-minor*` / `dev-major*` /
      `dev-alpha*` / `dev-beta*` / `dev-rc*` / `dev-stable*` branch
      name and `ci:version:precheck` passed (PEP 440, greater than all
      existing tags, no duplicate tag, source files consistent).
- [ ] `ci:version:postcheck` passed after `ci:version:write-config`
      (calls `release:verify-version`, three source files in sync,
      dev release semantics valid).
- [ ] `pyproject.toml`, `package.json`, and
      `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` versions
      are identical and were written by
      `task ci:version:write-config`.
- [ ] Build artifacts in `dist/*` carry SLSA Build L3 provenance from
      `actions/attest-build-provenance@v4.1.0`; downstream consumers
      can verify with
      `gh attestation verify <artifact> --repository xinvxueyuan/lingchu-bot`.
- [ ] `CHANGELOG.md` has a `## [<version>] - <date>` section with
      entries moved from `## [Unreleased]` and a bottom compare link.

## Impact Analysis (GitNexus / codegraph)

<!-- Briefly describe the symbols touched, direct callers, and risk
level. If the change is docs-only, say so. -->

## How to Verify

<!-- Concrete commands a reviewer can run to reproduce the result. -->

```bash
# e.g.
uv run -m pytest tests/path/to/test_xxx.py
pnpm --filter docs test
```

## Screenshots / Logs

<!-- Attach only if relevant. If your screenshots contain personal
information or third-party content, follow the anonymization rules in
Repository-Policy.md. -->

## Additional Notes

<!-- Anything reviewers should know: trade-offs, follow-up work,
known limitations. -->
