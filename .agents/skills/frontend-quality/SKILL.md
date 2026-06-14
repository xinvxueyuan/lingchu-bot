---
name: frontend-quality
description: Polish and diagnose React/frontend UI quality for the docs site (apps/docs), including responsive behavior, visual consistency, lint, accessibility, bundle, architecture, and regression risks. Use when finishing a docs site feature, fixing UI bugs, running react-doctor, cleaning React diagnostics, or improving visual polish and responsive states.
---

# Frontend Quality

Use this skill after or during frontend work on the docs site (`apps/docs`) when the visible experience or React health matters.

## Route

- For React diagnostics, lint, accessibility, bundle, architecture, or full local triage, read `references/react-doctor.md`.
- For visual polish, responsive states, layout consistency, and UI detail cleanup, read `references/frontend-polish.md`.

## Working Rules

- Verify the actual rendered UI when possible, not just the source.
- Check desktop and mobile constraints for text overflow, overlapping elements, and unstable controls.
- Prefer existing design-system patterns and local component conventions.
- Pair visual polish with functional regression checks when the change touches behavior.
- The docs site uses Next.js 16 + Fumadocs 16 + React 19 + Tailwind CSS 4 — use Context7 MCP for up-to-date framework docs.

## Project-Specific Commands

```bash
pnpm --filter docs lint          # ESLint for docs site
pnpm --filter docs test          # Vitest for docs site
pnpm --filter docs exec tsc --noEmit  # TypeScript check
npx react-doctor@latest --verbose --diff  # React health check (changed files)
```
