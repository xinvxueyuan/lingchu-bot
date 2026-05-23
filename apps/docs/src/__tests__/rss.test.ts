import { describe, it, expect, vi } from 'vitest';

vi.mock('@/lib/source', () => ({
  source: {
    getPages: vi.fn((locale: string) => {
      if (locale === 'zh') {
        return [
          { url: '/docs/a', data: { title: '页面A', description: '描述A', lastModified: '2025-01-01' } },
          { url: '/docs/b', data: { title: '页面B', description: '描述B' } },
          { url: '/docs/c', data: { title: '页面C' } },
        ];
      }
      return [
        { url: '/en/docs/a', data: { title: 'Page A', description: 'Desc A', lastModified: '2025-01-01' } },
      ];
    }),
  },
}));

import { getRSS } from '@/lib/rss';

describe('getRSS', () => {
  it('should return valid RSS XML string', () => {
    const result = getRSS('zh');
    expect(result).toContain('<?xml');
    expect(result).toContain('<rss');
    expect(result).toContain('</rss>');
  });

  it('should include zh title when locale is zh', () => {
    const result = getRSS('zh');
    expect(result).toContain('Lingchu Bot 文档');
  });

  it('should include en title when locale is en', () => {
    const result = getRSS('en');
    expect(result).toContain('Lingchu Bot Docs');
  });

  it('should include feed items from source pages', () => {
    const result = getRSS('zh');
    expect(result).toContain('页面A');
    expect(result).toContain('页面B');
  });

  it('should include pages even without description', () => {
    const result = getRSS('zh');
    expect(result).toContain('页面C');
  });

  it('should use baseUrl in feed id and link', () => {
    const result = getRSS('zh');
    expect(result).toContain('xinvxueyuan.github.io/lingchu-bot');
  });

  it('should default to zh locale', () => {
    const zhResult = getRSS();
    const explicitZh = getRSS('zh');
    expect(zhResult).toBe(explicitZh);
  });

  it('should include copyright with current year', () => {
    const result = getRSS('zh');
    expect(result).toContain(`All rights reserved ${new Date().getFullYear()}`);
  });
});
