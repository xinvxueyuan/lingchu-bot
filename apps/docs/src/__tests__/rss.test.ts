import { describe, it, expect, vi } from 'vitest';

vi.mock('@/lib/source', () => ({
  source: {
    getPages: vi.fn((locale: string) => {
      if (locale === 'en') {
        return [
          { url: '/docs/a', data: { title: 'Page A', description: 'Desc A', lastModified: '2025-01-01' } },
          { url: '/docs/b', data: { title: 'Page B', description: 'Desc B' } },
          { url: '/docs/c', data: { title: 'Page C' } },
        ];
      }
      return [
        { url: '/zh/docs/a', data: { title: '页面A', description: '描述A', lastModified: '2025-01-01' } },
      ];
    }),
  },
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
    expect(result).toContain('xinvxueyuan.github.io/lingchu-bot');
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
});
