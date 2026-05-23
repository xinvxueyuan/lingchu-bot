import { describe, it, expect } from 'vitest';

const defaultLocale = 'zh';

function switchLocale(pathname: string, currentLocale: string, targetLocale: string): string {
  const segments = pathname.split('/').filter((v) => v.length > 0);

  if (currentLocale === defaultLocale) {
    segments.unshift(targetLocale);
  } else if (targetLocale === defaultLocale) {
    if (segments[0] === currentLocale) segments.shift();
  } else {
    if (segments[0] === currentLocale) segments[0] = targetLocale;
    else segments.unshift(targetLocale);
  }

  return `/${segments.join('/')}`;
}

describe('switchLocale', () => {
  it('should switch from zh (default) to en', () => {
    expect(switchLocale('/docs/getting-started', 'zh', 'en')).toBe('/en/docs/getting-started');
  });

  it('should switch from en to zh (default)', () => {
    expect(switchLocale('/en/docs/getting-started', 'en', 'zh')).toBe('/docs/getting-started');
  });

  it('should handle root docs path from zh to en', () => {
    expect(switchLocale('/docs', 'zh', 'en')).toBe('/en/docs');
  });

  it('should handle root docs path from en to zh', () => {
    expect(switchLocale('/en/docs', 'en', 'zh')).toBe('/docs');
  });

  it('should handle home page from zh to en', () => {
    expect(switchLocale('/', 'zh', 'en')).toBe('/en');
  });

  it('should handle home page from en to zh', () => {
    expect(switchLocale('/en', 'en', 'zh')).toBe('/');
  });

  it('should handle switching between non-default locales', () => {
    expect(switchLocale('/en/docs/guide', 'en', 'ja')).toBe('/ja/docs/guide');
  });

  it('should handle switching when current locale prefix is missing', () => {
    expect(switchLocale('/docs/guide', 'en', 'ja')).toBe('/ja/docs/guide');
  });
});
