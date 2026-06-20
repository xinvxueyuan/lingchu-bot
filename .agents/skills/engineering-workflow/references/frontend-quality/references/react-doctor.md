# React Doctor

Scans React codebases for security, performance, correctness, and architecture issues. Outputs a 0-100 health score.

## After making React code changes

Run `npx react-doctor@latest --verbose --diff` and check the score did not regress.

If the score dropped, fix the regressions before committing.

## For general cleanup or code improvement

Run `npx react-doctor@latest --verbose` (without `--diff`) to scan the full codebase. Fix issues by severity — errors first, then warnings.

## Full local triage workflow

When the user asks for a full triage / cleanup pass (not just a regression check), fetch the canonical local-triage playbook and follow every step in it:

```bash
curl --fail --silent --show-error --header 'Cache-Control: no-cache' https://www.react.doctor/prompts/react-doctor-agent.md
```

The playbook is the single source of truth — a scan -> filter -> triage -> fix -> validate loop that edits the working tree directly (never commits, never opens PRs).

## Configuring or explaining rules

When the user wants to understand a rule, disagrees with one, or wants to disable / tune which rules run:

```bash
npx react-doctor@latest rules explain <rule>
npx react-doctor@latest rules disable|set|category|ignore-tag ...
```

This edits `doctor.config.*` (or `package.json#reactDoctor`). The project already has a `doctor.config.ts` at the root.

## Command

```bash
npx react-doctor@latest --verbose --diff
```

| Flag        | Purpose                                       |
| ----------- | --------------------------------------------- |
| `.`         | Scan current directory                        |
| `--verbose` | Show affected files and line numbers per rule |
| `--diff`    | Only scan changed files vs base branch        |
| `--score`   | Output only the numeric score                 |

## Project Context

- The docs site (`apps/docs`) uses Next.js 16 + Fumadocs 16 + React 19 + Tailwind CSS 4
- All server components and route handlers are async functions
- Client components use `useSyncExternalStore` instead of `useState` + `useEffect` for mount detection
- The project has a `🩺-react-doctor.yml` CI workflow that runs on PRs
