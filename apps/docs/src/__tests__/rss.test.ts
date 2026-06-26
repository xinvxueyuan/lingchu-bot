import { describe, it, expect, vi } from 'vitest';

vi.mock('@/lib/source', () => ({
  source: {
    getPages: vi.fn((locale: string) => {
      if (locale === 'en') {
        return [
          { url: '/docs/a', slugs: ['a'], locale: 'en', data: { title: 'Page A', description: 'Desc A', lastModified: '2025-01-01' } },
          { url: '/docs/b', slugs: ['b'], locale: 'en', data: { title: 'Page B', description: 'Desc B' } },
          { url: '/docs/c', slugs: ['c'], locale: 'en', data: { title: 'Page C' } },
        ];
      }
      return [
        { url: '/zh/docs/a', slugs: ['a'], locale: 'zh', data: { title: '页面A', description: '描述A', lastModified: '2025-01-01' } },
      ];
    }),
  },
  getPageImage: vi.fn((page: { url: string; locale: string }) => {
    // Mirror the real `getPageImage` shape: `/og/docs/<slugs>/image.png`
    // (en) or `/og/docs/zh/<slugs>/image.png` (zh). We only need the URL
    // segment here for assertion.
    if (page.locale === 'zh') {
      return { url: '/og/docs/zh/a/image.png' };
    }
    if (page.url === '/docs/a') return { url: '/og/docs/a/image.png' };
    if (page.url === '/docs/b') return { url: '/og/docs/b/image.png' };
    return { url: '/og/docs/c/image.png' };
  }),
}));

import { getRSS } from '@/lib/rss';

describe('getRSS', () => {
  it('should return valid RSS XML string', async () => {
    const result = await getRSS('en');
    expect(result).toContain('<?xml');
    expect(result).toContain('<rss');
    expect(result).toContain('</rss>');
  });

  it('should include en title when locale is en', async () => {
    const result = await getRSS('en');
    expect(result).toContain('Lingchu Bot Docs');
  });

  it('should include zh title when locale is zh', async () => {
    const result = await getRSS('zh');
    expect(result).toContain('Lingchu Bot 文档');
  });

  it('should include feed items from source pages', async () => {
    const result = await getRSS('en');
    expect(result).toContain('Page A');
    expect(result).toContain('Page B');
  });

  it('should include pages even without description', async () => {
    const result = await getRSS('en');
    expect(result).toContain('Page C');
  });

  it('should use baseUrl in feed id and link', async () => {
    const result = await getRSS('en');
    expect(result).toContain('lingchu.zone.id');
  });

  it('should default to en locale', async () => {
    const enResult = await getRSS();
    const explicitEn = await getRSS('en');
    expect(enResult).toBe(explicitEn);
  });

  it('should include copyright with current year', async () => {
    const result = await getRSS('en');
    expect(result).toContain(`All rights reserved ${new Date().getFullYear()}`);
  });

  it('should include an author element per item', async () => {
    const result = await getRSS('en');
    // The `feed` library emits a per-item `<author>` element when the
    // `Feed.author` config is set, even though the strict RSS 2.0 form
    // is the Dublin Core `<dc:creator>`. We assert the more lenient
    // `<author>` form so the test stays in sync with the library.
    expect(result).toContain('<author>Lingchu Bot Docs</author>');
  });

  it('should include a pubDate per item', async () => {
    const result = await getRSS('en');
    expect(result).toMatch(/<pubDate>[^<]+<\/pubDate>/);
  });

  it('should include an image enclosure per item', async () => {
    const result = await getRSS('en');
    // The feed library emits `image` as `<enclosure url="..." type="...">`
    // alongside an `<image><url>...</url></image>` block.
    expect(result).toMatch(/<enclosure[^>]+url="https:\/\/lingchu\.zone\.id\/og\/docs\/a\/image\.png"/);
  });

  it('should expose the feed self link', async () => {
    const result = await getRSS('en');
    expect(result).toContain('<atom:link href="https://lingchu.zone.id/rss.xml"');
  });
});
