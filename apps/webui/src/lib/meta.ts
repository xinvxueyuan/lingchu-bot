import i18n from "@/i18n";

/**
 * 所有页面的通用 meta：标题与描述来自 i18n（构建期预渲染时以回退语言运行）。
 * 路由 meta 保持 `({}: Route.MetaArgs)` 签名后委托至此，以复用文案。
 */
export function appPageMeta() {
  return [
    { title: i18n.t("app.title") },
    { name: "description", content: i18n.t("app.tagline") },
  ];
}
