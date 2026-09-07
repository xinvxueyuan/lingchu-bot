import { useTranslation } from "react-i18next";
import { TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

/** 「后端已运行但未连接 OneBot11」守卫横幅：警示样式 + 引导文案 + 手动刷新。 */
export function OnebotDisconnectedBanner({ onRefresh }: { onRefresh: () => void }) {
  const { t } = useTranslation();
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3"
    >
      <TriangleAlert className="size-5 shrink-0 text-destructive" aria-hidden />
      <div className="grid min-w-0 flex-1 gap-0.5">
        <p className="font-medium text-destructive">{t("overview.onebotDisconnected.title")}</p>
        <p className="text-sm text-destructive/80">{t("overview.onebotDisconnected.desc")}</p>
      </div>
      <Button type="button" variant="outline" size="sm" onClick={onRefresh}>
        {t("overview.onebotDisconnected.refresh")}
      </Button>
    </div>
  );
}
