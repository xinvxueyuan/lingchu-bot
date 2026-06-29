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
- [ ] For code changes, I ran `gitnexus_impact` (or the equivalent
      analysis) and recorded the blast radius below.
- [ ] For code changes, I have run `uv run -m ruff check .`,
      `uv run -m ruff format --check .`, `uv run -m pyright .`, and
      `uv run -m ty check .` locally.
- [ ] For docs site changes, I have run `pnpm --filter docs lint` and
      `pnpm --filter docs test` locally.
- [ ] I have added or updated tests covering the change.
- [ ] I have updated relevant documentation, i18n strings, runtime
      config, and handle defaults as needed.

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
