# Debug Investigation

Use this skill for bugs, regressions, flakes, and performance problems. The core job is to build a reliable feedback loop, use it to locate the cause, make the smallest correct fix, and prove the regression is covered.

## Phase 1: Build The Loop

Do not start by staring at code. First create or find an agent-runnable pass/fail signal that reproduces the user's symptom.

Try these in order:

1. A failing unit, integration, or e2e test.
2. A CLI command or HTTP request with fixture input.
3. A captured trace, payload, event log, or core dump replayed in isolation.
4. A throwaway harness around the smallest service or function.
5. A property, fuzz, stress, or repeated-run loop for intermittent failures.
6. A bisection or differential loop across commits, versions, configs, or datasets.

Improve the loop before trusting it: make it faster, sharper, and more deterministic. For flakes, raise the reproduction rate with repetition, parallelism, stress, injected sleeps, pinned time, or fixed seeds.

If no loop can be built, stop and ask for the missing artifact or environment: logs, screen recording with timestamps, repro data, access, or permission to add temporary instrumentation.

## Phase 2: Reproduce

Run the loop and confirm:

- It shows the same failure mode the user reported.
- It reproduces across multiple runs, or at a high enough rate for a flaky bug.
- The assertion is specific to the symptom, not just "did not crash".

Wrong repro means wrong fix. Tighten the loop before proceeding.

## Phase 3: Localize

Trace the failing path from symptom to source.

- Inspect recent changes, ownership boundaries, and related tests.
- Use logs, breakpoints, probes, or temporary instrumentation where they answer a specific question.
- Form one hypothesis at a time and design the next command to falsify it.
- Prefer bisection or differential checks when the regression window is known.
- Use `gitnexus-exploring` to trace execution flows and `gitnexus-debugging` for structured debugging.
- Remove temporary instrumentation once it has served its purpose.

## Phase 4: Fix

Make the smallest fix that addresses the cause, not merely the observed symptom.

- Keep unrelated refactors out of the patch.
- Preserve existing public contracts unless the user explicitly wants a behavior change.
- If data migration, config, timing, cache, or concurrency is involved, verify both old and new paths.
- Run `gitnexus-impact-analysis` before editing to assess blast radius.

## Phase 5: Verify

Prove the fix with evidence:

- The original loop fails before the fix and passes after it, when possible.
- Add or update a regression test at the highest useful seam.
- Run nearby tests and any broader checks proportionate to the blast radius.
- Run `gitnexus detect_changes` to verify only expected symbols are affected.
- Report the exact commands run and what they proved.

## Output

When done, summarize:

- The reproduced symptom.
- The root cause.
- The fix.
- The regression coverage and remaining risk.
