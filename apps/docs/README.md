# Lingchu Bot Docs App

This is the Fumadocs/Next.js static documentation app for Lingchu Bot.
Its documentation source lives in `content/docs`.

Run commands from the repository root with pnpm:

```bash
pnpm --filter docs dev
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs run lint:links
pnpm turbo run build --filter=docs
```

Open [localhost:3000](http://localhost:3000) with your browser.

The root `Taskfile.yml` is the preferred automation surface for cross-project work. Use `task check`, `task test`, `task build`, or `task ci` when a change spans Python code, docs, packages, and shared tooling.

## Environment variables

| Name | Purpose | Default |
| --- | --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Absolute site URL used by `metadataBase`, `openGraph`, `twitter`, and RSS feed ids. Set this when deploying to a custom domain or a preview environment. Trailing slashes are trimmed. | `https://lingchu.zone.id/` |

`output: 'export'` resolves the value at build time, so set the variable in the CI environment that runs `next build`.

## Explore

Important files:

- `source.config.ts`: configures Fumadocs MDX collections.
- `src/lib/source.ts`: configures Fumadocs source loading.
- `src/lib/i18n.ts`: defines the `zh` and `en` source locales.

| Route                     | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| `app/(home)`              | The language landing page.                             |
| `app/docs`                | English documentation (default locale).                |
| `app/zh/docs`             | Simplified Chinese documentation.                      |
| `app/api/search/route.ts` | Static search index route.                             |
