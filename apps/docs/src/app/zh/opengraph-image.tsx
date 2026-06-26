import { ImageResponse } from 'next/og';
import { generate as DefaultImage } from 'fumadocs-ui/og';
import { appName } from '@/lib/shared';

// `app/zh/opengraph-image.tsx` mirrors the root `opengraph-image.tsx`
// under the `/zh` route so the Chinese home page (`getHomeMetadata('zh')`)
// resolves `og:image` / `twitter:image` against a real PNG at
// `out/zh/opengraph-image`. The English version only renders at
// `out/opengraph-image`; without this file the Chinese home `<meta>` tags
// would point to a 404 in the static export.

export const runtime = 'nodejs';
// `output: 'export'` requires every file-convention route to be statically
// generated; declaring these exports silences the `force-static` warning.
export const dynamic = 'force-static';
export const revalidate = false;
export const alt = `${appName} 文档`;
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default async function Image() {
  return new ImageResponse(
    <DefaultImage
      title={`${appName} 文档`}
      description="基于 NoneBot2 的 QQ 群管理机器人文档"
      site={appName}
    />,
    size,
  );
}
