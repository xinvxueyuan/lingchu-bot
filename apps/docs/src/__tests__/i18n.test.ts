import { describe, it, expect } from 'vitest';
import { i18n } from '@/lib/i18n';

describe('i18n', () => {
  it('should have en as default language', () => {
    expect(i18n.defaultLanguage).toBe('en');
  });

  it('should include en and zh languages', () => {
    expect(i18n.languages).toContain('en');
    expect(i18n.languages).toContain('zh');
  });

  it('should have exactly 2 languages', () => {
    expect(i18n.languages).toHaveLength(2);
  });
});
