import { docs } from 'collections/server';
import { i18n } from './i18n';
import { loader } from 'fumadocs-core/source';
import { lucideIconsPlugin } from 'fumadocs-core/source/lucide-icons';
import { docsContentRoute, docsImageRoute, docsRoute } from './shared';

// See https://fumadocs.dev/docs/headless/source-api for more info
export const source = loader({
  baseUrl: docsRoute,
  i18n,
  source: docs.toFumadocsSource(),
  plugins: [lucideIconsPlugin()],
});

export function getPageImage(page: (typeof source)['$inferPage']) {
  const segments =
    page.locale === 'zh' ? ['zh', ...page.slugs, 'image.png'] : [...page.slugs, 'image.png'];

  return {
    segments,
    url: `${docsImageRoute}/${segments.join('/')}`,
  };
}

/**
 * Resolve the canonical `page.url` of the same-slug page in the *other*
 * locale. Returns `undefined` when the alternate locale has no page for the
 * same `slugs`. Used by `getDocsPageMetadata` and `sitemap.ts` to keep
 * cross-locale hreflang and `alternates.languages` consistent.
 */
export function getAlternateUrl(page: (typeof source)['$inferPage']): string | undefined {
  const otherLocale = page.locale === 'zh' ? 'en' : 'zh';
  const other = source.getPage(page.slugs, otherLocale);
  return other ? other.url : undefined;
}

export function getPageMarkdownUrl(page: (typeof source)['$inferPage']) {
  const segments =
    page.locale === 'zh' ? ['zh', ...page.slugs, 'content.md'] : [...page.slugs, 'content.md'];

  return {
    segments,
    url: `${docsContentRoute}/${segments.join('/')}`,
  };
}

export async function getLLMText(page: (typeof source)['$inferPage']) {
  const processed = await page.data.getText('processed');

  return `# ${page.data.title} (${page.url})

${processed}`;
}
