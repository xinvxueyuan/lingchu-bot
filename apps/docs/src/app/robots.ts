import type { MetadataRoute } from 'next';
import { getSiteUrlString } from '@/lib/site-metadata';

// `app/robots.ts` is a Next.js file convention that emits
// `out/robots.txt` at build time. The sitemap URL is resolved from
// `getSiteUrlString()` so the deployment domain stays in sync with
// `metadataBase` and the RSS feeds.

// `output: 'export'` requires the route to be statically generated.
export const dynamic = 'force-static';
export const revalidate = false;

export default function robots(): MetadataRoute.Robots {
  const base = getSiteUrlString();
  return {
    rules: [{ userAgent: '*', allow: '/' }],
    sitemap: `${base}/sitemap.xml`,
  };
}
