import { describe, it, expect } from 'vitest';

const defaultLocale = 'en';

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
  it('should switch from en (default) to zh', () => {
    expect(switchLocale('/docs/getting-started', 'en', 'zh')).toBe('/zh/docs/getting-started');
  });

  it('should switch from zh to en (default)', () => {
    expect(switchLocale('/zh/docs/getting-started', 'zh', 'en')).toBe('/docs/getting-started');
  });

  it('should handle root docs path from en to zh', () => {
    expect(switchLocale('/docs', 'en', 'zh')).toBe('/zh/docs');
  });

  it('should handle root docs path from zh to en', () => {
    expect(switchLocale('/zh/docs', 'zh', 'en')).toBe('/docs');
  });

  it('should handle home page from en to zh', () => {
    expect(switchLocale('/', 'en', 'zh')).toBe('/zh');
  });

  it('should handle home page from zh to en', () => {
    expect(switchLocale('/zh', 'zh', 'en')).toBe('/');
  });

  it('should handle switching between non-default locales', () => {
    expect(switchLocale('/zh/docs/guide', 'zh', 'ja')).toBe('/ja/docs/guide');
  });

  it('should handle switching when current locale prefix is missing', () => {
    expect(switchLocale('/docs/guide', 'zh', 'ja')).toBe('/ja/docs/guide');
  });
});
