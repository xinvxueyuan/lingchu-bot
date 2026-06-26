import type { MetadataRoute } from 'next';
import { appName } from '@/lib/shared';

// `app/manifest.ts` is a Next.js file convention that emits
// `out/manifest.webmanifest` at build time. The manifest keeps the docs
// site installable as a PWA target. Theme + background colors are
// placeholders aligned with the current default Fumadocs light/dark
// palette; adjust as the brand evolves.

// `output: 'export'` requires the route to be statically generated.
export const dynamic = 'force-static';
export const revalidate = false;

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: appName,
    short_name: appName,
    description: `${appName} documentation site`,
    start_url: '/',
    display: 'standalone',
    theme_color: '#0f172a',
    background_color: '#ffffff',
    icons: [
      { src: '/favicon.ico', sizes: 'any', type: 'image/x-icon' },
    ],
  };
}
