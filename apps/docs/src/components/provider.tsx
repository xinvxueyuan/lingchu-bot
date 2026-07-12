"use client";
import { RootProvider } from "fumadocs-ui/provider/next";
import { i18nProvider } from "fumadocs-ui/i18n";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useCallback } from "react";
import SearchDialog from "@/components/search";
import { translations } from "@/lib/layout.shared";
import { switchLocale } from "@/lib/locale";

export function Provider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const locale = pathname.startsWith("/zh") ? "zh" : "en";

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
