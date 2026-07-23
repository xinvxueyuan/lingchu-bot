"use client";
import { RootProvider } from "fumadocs-ui/provider/next";
import { i18nProvider } from "fumadocs-ui/i18n";
import { usePathname } from "next/navigation";
import { type ReactNode, useCallback } from "react";
import SearchDialog from "@/components/search";
import { translations } from "@/lib/layout.shared";
import { switchLocale } from "@/lib/locale";
import { TransitionLink, useViewTransitionRouter } from "@/components/view-transition";

export function Provider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { push } = useViewTransitionRouter();
  const locale = pathname.startsWith("/zh") ? "zh" : "en";

  const onLocaleChange = useCallback(
    (newLocale: string) => {
      push(switchLocale(pathname, locale, newLocale), { types: ["locale-switch"] });
    },
    [pathname, locale, push],
  );

  return (
    <RootProvider
      i18n={{ ...i18nProvider(translations, locale), onLocaleChange }}
      search={{ SearchDialog }}
      components={{ Link: TransitionLink }}
    >
      {children}
    </RootProvider>
  );
}
