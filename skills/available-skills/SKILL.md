---
name: available-skills
description: Project-local index of currently available Codex skills and plugins for Lingchu Bot. Use when an agent needs to choose which skill to load for documentation lookup, code intelligence, browser verification, artifact editing, deployment, or skill authoring in this repository.
---

# Available Skills

Use this file as a compact routing table. Do not load every external skill preemptively; load the specific `SKILL.md` only after the user request matches its trigger.

## Mandatory Documentation Rule

When the user asks about a library, framework, SDK, API, CLI tool, or cloud service, use Context7 MCP or `find-docs` for current documentation. Start with `resolve-library-id` unless the user gives an exact `/org/project` ID, then query docs with the full user question. Prefer documentation lookup over web search for developer docs.

## Project-Local Skills

- `gitnexus/gitnexus-exploring`: understand architecture, execution flows, and unfamiliar code.
- `gitnexus/gitnexus-impact-analysis`: assess blast radius before changing symbols.
- `gitnexus/gitnexus-debugging`: trace errors, failures, and unexpected behavior.
- `gitnexus/gitnexus-refactoring`: rename, extract, split, move, or restructure code safely.
- `gitnexus/gitnexus-guide`: answer questions about GitNexus tools, schema, and workflow.
- `gitnexus/gitnexus-cli`: run GitNexus CLI tasks such as analyze, status, clean, wiki, and repo listing.
- `prek`: set up or run `prek` hook checks.

## Coding And Repository Skills

- `github:*`: inspect GitHub repositories, PRs, issues, review comments, CI failures, and publish flows.
- `gitnexus-pr-review`: review pull requests and assess merge risk.
- `context7-mcp` / `find-docs`: fetch current developer documentation.
- `openai-docs`: answer OpenAI product and API questions from official docs.

## Frontend And Browser Skills

- `browser:control-in-app-browser`: open, inspect, click, screenshot, and verify local web targets in the Codex browser.
- `playwright`: automate browser flows from the terminal.
- `chrome:control-chrome`: use the user's Chrome state when cookies, tabs, or extensions matter.
- `vercel:nextjs`, `vercel:react-best-practices`, `vercel:shadcn`, `vercel:verification`, and related Vercel skills: build, verify, and deploy frontend work.

## Cloud And Platform Skills

- `cloudflare:*`: Workers, Wrangler, Durable Objects, Agents SDK, MCP servers, sandbox SDK, and Cloudflare platform work.
- `vercel:*`: Vercel deployments, API/CLI, auth, storage, payments, functions, queues, workflow, observability, and AI SDK integrations.

## Artifact Skills

- `documents:documents`: create, edit, redline, and verify Word documents.
- `presentations:Presentations`: create, edit, render, and verify slide decks.
- `spreadsheets:Spreadsheets`: create, edit, analyze, visualize, and export spreadsheets.
- `pdf`: read, create, or review PDFs with visual checks when layout matters.
- `imagegen`: generate or edit raster images.

## Skill And Plugin Authoring

- `skill-creator`: create or update skills with concise `SKILL.md` files and optional resources.
- `skill-installer`: install Codex skills.
- `plugin-creator`: scaffold Codex plugins.

## Understand-Anything Skills

Use `understand-anything:*` when the task explicitly asks for repository graphs, dashboards, onboarding guides, domain extraction, diff analysis, or deep explanations using the Understand Anything plugin.
