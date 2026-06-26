import { ImageResponse } from 'next/og';
import { generate as DefaultImage } from 'fumadocs-ui/og';
import { appName } from '@/lib/shared';

// `app/opengraph-image.tsx` is a Next.js file convention that emits a
// 1200x630 PNG at `out/opengraph-image.png` and the locale variant
// `out/zh/opengraph-image.png` for the default + zh roots. The `image`
// metadata in `getHomeMetadata` references these paths so social cards
// render with the site brand.

export const runtime = 'nodejs';
// `output: 'export'` requires every file-convention route to be statically
// generated; declaring these exports silences the `force-static` warning.
export const dynamic = 'force-static';
export const revalidate = false;
export const alt = `${appName} documentation`;
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default async function Image() {
  return new ImageResponse(
    <DefaultImage title={appName} description="Documentation" site={appName} />,
    size,
  );
}
