import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// 用 Vite 的 import.meta.glob 在构建期同步收集所有 locale JSON（无需 http-backend），
// 与 react-i18next 官方 Vite Quick Start 一致；构建期预渲染（Node）下安全。
const modules = import.meta.glob("./locales/*.json", {
  eager: true,
}) as Record<string, { default: Record<string, unknown> }>;

const resources: Record<string, { translation: Record<string, unknown> }> = {};
for (const [path, mod] of Object.entries(modules)) {
  const lng = path.split("/").pop()!.replace(/\.json$/, "");
  resources[lng] = { translation: mod.default as Record<string, unknown> };
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    // 项目为灵初（中文）Bot，默认回退 zh-CN
    fallbackLng: "zh-CN",
    supportedLngs: ["zh-CN", "en-US"],
    detection: {
      // 顺序与 entry.server 的 SSR 解析（Cookie → Accept-Language）对齐，
      // 避免客户端首次渲染与 SSR 的 <html lang> 不一致导致 hydration mismatch。
      order: ["cookie", "localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "lingchu-lng",
      lookupCookie: "lingchu-lng",
    },
    interpolation: { escapeValue: false },
    react: { useSuspense: false },
  });

export const SUPPORTED_LNGS = ["zh-CN", "en-US"] as const;
export type AppLanguage = (typeof SUPPORTED_LNGS)[number];
export default i18n;
