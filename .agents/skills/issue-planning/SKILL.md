---
name: issue-planning
description: Shape product and engineering work into PRDs, issues, triage states, QA reports, and refactor plans. Use when the user wants a PRD, tickets/issues, issue triage, refactor RFC, tracer-bullet breakdown, or domain glossary for the Lingchu Bot project.
---

# Issue Planning

Use this skill to turn conversation, bugs, plans, and domain language into trackable work.

## Route

- For PRDs, read `references/to-prd.md`.
- For breaking plans into issues, read `references/to-issues.md`.
- For issue state management and incoming issue triage, read `references/triage.md`.
- For refactor RFCs and tiny-commit plans, read `references/request-refactor-plan.md`.

## Working Rules

- Preserve the target issue tracker and label vocabulary from repo docs.
- Keep issues independently grabbable and vertical when implementation is involved.
- Ask only the tradeoff questions needed to avoid filing misleading work.
- Save outputs where the referenced guide expects them.
- Use GitHub MCP tools (`mcp_GitHub_*`) for creating and managing issues/PRs.

## Project Context

- Issue tracker: GitHub Issues (use `mcp_GitHub_create_issue`, `mcp_GitHub_list_issues`)
- PRs: GitHub Pull Requests (use `mcp_GitHub_create_pull_request`, `mcp_GitHub_list_pull_requests`)
- Domain: NoneBot2 group management bot with OneBot V11 / Milky / QQ adapters
- Tech stack: Python 3.13 backend, Next.js 16 docs site
