import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** 占位卡：标题 + 「内容占位」描述；children 非空时额外渲染在内容区（如操作按钮）。 */
export function PlaceholderCard({ title, children }: { title: string; children?: ReactNode }) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{t("tabs.placeholder")}</CardDescription>
      </CardHeader>
      {children ? <CardContent>{children}</CardContent> : null}
    </Card>
  );
}
