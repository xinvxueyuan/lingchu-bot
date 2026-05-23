# Lingchu Bot Docs App

This is the Fumadocs/Next.js static documentation app for Lingchu Bot.
Its documentation source lives in `content/docs`.

Run the development server:

```bash
npm run dev
# or
pnpm dev
# or
yarn dev
```

Open [localhost:3000](http://localhost:3000) with your browser.

## Explore

Important files:

- `source.config.ts`: configures Fumadocs MDX collections.
- `src/lib/source.ts`: configures Fumadocs source loading.
- `src/lib/i18n.ts`: defines the `zh` and `en` source locales.

| Route                     | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| `app/(home)`              | The language landing page.                             |
| `app/docs`                | Simplified Chinese documentation.                      |
| `app/en/docs`             | English documentation.                                 |
| `app/api/search/route.ts` | Static search index route.                             |
