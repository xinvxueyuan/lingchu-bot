import { source } from '@/lib/source';
import { exportEpub } from 'fumadocs-epub';
import { appName, gitConfig } from '@/lib/shared';

export const revalidate = false;

export async function GET(): Promise<Response> {
  const buffer = await exportEpub({
    source,
    title: `${appName} Documentation`,
    author: gitConfig.user,
    description: `Documentation for the NoneBot2-based application-side management bot`,
    language: 'en',
    includePages: (page) => page.locale !== 'zh',
  });

  return new Response(new Uint8Array(buffer), {
    headers: {
      'Content-Type': 'application/epub+zip',
      'Content-Disposition': `attachment; filename="${appName.toLowerCase()}-docs-en.epub"`,
    },
  });
}
