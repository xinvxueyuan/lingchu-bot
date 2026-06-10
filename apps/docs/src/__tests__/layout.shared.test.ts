import { describe, it, expect } from 'vitest';
import { baseOptions, translations } from '@/lib/layout.shared';

describe('layout.shared', () => {
  describe('baseOptions', () => {
    it('should return en options by default', async () => {
      const options = await baseOptions();
      expect(options.nav?.title).toBe('Lingchu Bot');
      expect(options.githubUrl).toContain('xinvxueyuan');
      expect(options.githubUrl).toContain('lingchu-bot');
    });

    it('should return en docs link for en locale', async () => {
      const options = await baseOptions('en');
      const docsLink = options.links?.find(
        (l) => 'text' in l && l.text === 'Docs',
      );
      expect(docsLink).toBeDefined();
      expect(docsLink).toHaveProperty('url', '/docs');
    });

    it('should return zh docs link for zh locale', async () => {
      const options = await baseOptions('zh');
      const docsLink = options.links?.find(
        (l) => 'text' in l && l.text === '文档',
      );
      expect(docsLink).toBeDefined();
      expect(docsLink).toHaveProperty('url', '/zh/docs');
    });

    it('should include githubUrl for auto-generated icon link', async () => {
      const options = await baseOptions();
      expect(options.githubUrl).toBe('https://github.com/xinvxueyuan/lingchu-bot');
    });
  });

  describe('translations', () => {
    it('should be defined', () => {
      expect(translations).toBeDefined();
    });
  });
});
