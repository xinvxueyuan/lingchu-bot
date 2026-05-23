import { describe, it, expect } from 'vitest';
import { i18n } from '@/lib/i18n';

describe('i18n', () => {
  it('should have zh as default language', () => {
    expect(i18n.defaultLanguage).toBe('zh');
  });

  it('should include zh and en languages', () => {
    expect(i18n.languages).toContain('zh');
    expect(i18n.languages).toContain('en');
  });

  it('should have exactly 2 languages', () => {
    expect(i18n.languages).toHaveLength(2);
  });
});
