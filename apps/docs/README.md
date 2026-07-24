# Lingchu Bot Docs App

This is the Astro Starlight static documentation app for Lingchu Bot. Its
documentation source lives in `src/content/docs`.

Run commands from the repository root with pnpm:

```bash
pnpm --filter docs dev
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs check-types
pnpm turbo run build --filter=docs
```

Open [localhost:4321](http://localhost:4321) with your browser during local
development.

The root `Taskfile.yml` is the preferred automation surface for cross-project
work. Use `task check`, `task test`, `task build`, or `task ci` when a change
spans Python code, docs, packages, and shared tooling.

## Structure

| Path | Description |
| --- | --- |
| `astro.config.mjs` | Starlight integration, locales, sidebar, Tailwind, and React islands. |
| `src/content.config.ts` | Starlight docs content collection schema. |
| `src/content/docs` | English documentation, served as the root locale. |
| `src/content/docs/zh` | Simplified Chinese documentation. |
| `src/styles/global.css` | Starlight/Tailwind theme bridge and shared docs styles. |
