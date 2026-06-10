import { describe, it, expect } from 'vitest';
import { docsImageRoute, docsContentRoute } from '@/lib/shared';

function buildSegments(slugs: string[], locale: string): string[] {
  return locale === 'zh' ? ['zh', ...slugs, 'image.png'] : [...slugs, 'image.png'];
}

function buildContentSegments(slugs: string[], locale: string): string[] {
  return locale === 'zh' ? ['zh', ...slugs, 'content.md'] : [...slugs, 'content.md'];
}

describe('source utilities', () => {
  describe('getPageImage URL generation', () => {
    it('should generate correct en image URL structure', () => {
      const slugs = ['getting-started'];
      const segments = buildSegments(slugs, 'en');
      const url = `${docsImageRoute}/${segments.join('/')}`;

      expect(url).toBe('/og/docs/getting-started/image.png');
      expect(segments).toEqual(['getting-started', 'image.png']);
    });

    it('should generate correct zh image URL structure', () => {
      const slugs = ['getting-started'];
      const segments = buildSegments(slugs, 'zh');
      const url = `${docsImageRoute}/${segments.join('/')}`;

      expect(url).toBe('/og/docs/zh/getting-started/image.png');
      expect(segments).toEqual(['zh', 'getting-started', 'image.png']);
    });

    it('should handle nested slugs', () => {
      const slugs = ['developer-guide', 'commit-style'];
      const segments = buildSegments(slugs, 'en');
      const url = `${docsImageRoute}/${segments.join('/')}`;

      expect(url).toBe('/og/docs/developer-guide/commit-style/image.png');
    });
  });

  describe('getPageMarkdownUrl URL generation', () => {
    it('should generate correct en markdown URL structure', () => {
      const slugs = ['getting-started'];
      const segments = buildContentSegments(slugs, 'en');
      const url = `${docsContentRoute}/${segments.join('/')}`;

      expect(url).toBe('/llms.mdx/docs/getting-started/content.md');
    });

    it('should generate correct zh markdown URL structure', () => {
      const slugs = ['getting-started'];
      const segments = buildContentSegments(slugs, 'zh');
      const url = `${docsContentRoute}/${segments.join('/')}`;

      expect(url).toBe('/llms.mdx/docs/zh/getting-started/content.md');
    });
  });
});
