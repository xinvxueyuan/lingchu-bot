# Change Review

Use this skill for code review. Default to a defect-focused review: findings first, ordered by severity, with file and line references. Keep summaries brief and secondary.

## Review Modes

- **Code review**: use when the user asks for a general review or provides a diff, PR, branch, or files.
- **Fixed-point review**: use when the user says "review since X", names a branch, commit, tag, or merge-base.
- **Spec review**: use when the user provides an issue, PRD, spec, acceptance criteria, or asks whether the implementation matches what was requested.
- **Standards review**: use when the repo has documented standards or the user asks whether the change follows project conventions.

If a fixed point is needed but missing, ask: "Review against what: a branch, a commit, or main?"

## Gather Evidence

For a fixed-point review:

1. Capture changed files with `git diff --name-only <fixed-point>...HEAD`.
2. Capture commits with `git log <fixed-point>..HEAD --oneline`.
3. Read the relevant diff hunks, not only filenames.

For a spec review, look for the spec in this order:

1. Issue or PR references in commits.
2. A path or URL supplied by the user.
3. PRD/spec files under `docs/`, `specs/`, or `.scratch/`.
4. Conversation context.

For a standards review, collect relevant standards sources:

- `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`
- `.github/note/AGENTS-zh.md`
- `docs/adr/`
- Config files such as `.editorconfig`, `eslint`, `ruff`, `pyright`, `tsconfig`

## Review Checklist

Prioritize issues that can break users or future maintainers:

- Correctness and behavioral regressions.
- Security and privacy problems.
- Data loss, migration, caching, concurrency, timing, or transaction bugs.
- Missing or weak tests for changed behavior.
- Spec requirements that are missing, partial, or implemented with different semantics.
- Scope creep: behavior not asked for that changes risk.
- Violations of documented standards that tooling will not catch.
- Performance or reliability regressions with plausible user impact.
- Adapter API differences (OneBot V11 vs Milky) not handled correctly.
- Missing i18n updates when user-facing strings change.

## Output Format

Lead with findings:

```md
## Findings

- [P1] Title
  File reference. Explain the bug, why it matters, and the minimal condition that triggers it.

## Open Questions

- ...

## Summary

Brief change summary or "No findings."
```

If there are no findings, say that clearly and mention any residual risk or test gaps.
