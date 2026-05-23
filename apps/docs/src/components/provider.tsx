'use client';
import SearchDialog from '@/components/search';
import { RootProvider } from 'fumadocs-ui/provider/next';
import { i18nProvider } from 'fumadocs-ui/i18n';
import { usePathname, useRouter } from 'next/navigation';
import { type ReactNode, useCallback } from 'react';
import { translations } from '@/lib/layout.shared';
import { i18n } from '@/lib/i18n';

const defaultLocale = i18n.defaultLanguage;

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

export function Provider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const locale = pathname.startsWith('/en') ? 'en' : 'zh';

  const onLocaleChange = useCallback(
    (newLocale: string) => {
      router.push(switchLocale(pathname, locale, newLocale));
    },
    [pathname, locale, router],
  );

  return (
    <RootProvider
      i18n={{ ...i18nProvider(translations, locale), onLocaleChange }}
      search={{ SearchDialog }}
    >
      {children}
    </RootProvider>
  );
}
