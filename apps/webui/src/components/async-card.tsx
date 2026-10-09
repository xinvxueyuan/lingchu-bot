import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** 异步区块通用卡片：独立的 loading / 错误态，就绪时渲染子内容。 */
export function AsyncCard({
  title,
  pending,
  error,
  children,
}: {
  title: string;
  pending: boolean;
  /** true → 默认「加载失败」文案；ReactNode → 自定义错误/空态内容。 */
  error?: boolean | ReactNode;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {pending ? (
          <p className="text-sm text-muted-foreground">{t("overview.loading")}</p>
        ) : error ? (
          typeof error === "boolean" ? (
            <p role="alert" className="text-sm text-destructive">
              {t("overview.loadError")}
            </p>
          ) : (
            error
          )
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
