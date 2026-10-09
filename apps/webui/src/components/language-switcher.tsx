import i18n from "@/i18n";
import { SUPPORTED_LNGS, type AppLanguage } from "@/i18n";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

export function LanguageSwitcher() {
  const { t, i18n: i18 } = useTranslation();
  const current = (i18.resolvedLanguage ?? "zh-CN") as AppLanguage;

  function switchTo(lng: AppLanguage) {
    void i18n.changeLanguage(lng).then(() => {
      if (typeof document !== "undefined") {
        document.documentElement.lang = lng;
        // localStorage 由 languageDetector 自动缓存；Cookie 仅为 SSR 往返一致，
        // 服务端渲染时可据此解析 <html lang>。
        document.cookie =
          "lingchu-lng=" + encodeURIComponent(lng) + "; path=/; max-age=31536000";
      }
    });
  }

  return (
    <div
      className="inline-flex items-center gap-1"
      role="group"
      aria-label={t("app.title")}
    >
      {SUPPORTED_LNGS.map((lng) => (
        <Button
          key={lng}
          type="button"
          size="sm"
          variant={lng === current ? "default" : "outline"}
          aria-pressed={lng === current}
          onClick={() => switchTo(lng)}
        >
          {t(`language.${lng}`)}
        </Button>
      ))}
    </div>
  );
}
