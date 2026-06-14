---
name: delivery-loop
description: Run disciplined implementation loops for debugging, test-driven development, and code-review validation. Use when the user reports a bug, failure, flaky test, performance issue, asks for TDD or red-green-refactor, wants implementation verification, or requests a review of code, a branch, PR, or worktree changes.
---

# Delivery Loop

Use this skill when the task is about getting code from uncertain to verified: reproduce, test, fix, review, and tighten.

## Route

- For bugs, crashes, flaky behavior, slow paths, and "why is this failing", read `references/debug-investigation.md`.
- For explicit TDD or test-first work, read `references/tdd.md`, then load its focused references only as needed.
- For reviews of code, diffs, branches, or PRs, read `references/change-review.md` and lead with findings.

## Loop

1. Reproduce or inspect the current state before changing code.
2. Add or choose the smallest useful failing check when feasible.
3. Implement narrowly, preserving user changes in the worktree.
4. Run targeted validation first, then broaden only when risk warrants it.
5. Summarize what changed and which checks ran.

Use `gitnexus-exploring` or `gitnexus-impact-analysis` alongside this skill when dependency impact, graph exploration, or PR structure needs deeper context.

## Project-Specific Checks

After fixes or changes, run the relevant checks from the Quick Reference table in `AGENTS.md`:

| What changed | Minimum checks |
|---|---|
| Python source | `ruff check` + `ruff format --check` + `pyright` + `ty check` + `pytest` |
| Docs site | `pnpm --filter docs lint` + `pnpm --filter docs test` + `tsc --noEmit` |
| Mixed / unsure | `task check && task test` |

For GitNexus-verified changes, also run `gitnexus detect_changes` before committing.
