import { useTranslation } from "react-i18next";

import { PageContainer } from "@/components/page-container";
import { useActivePageTab } from "@/components/page-tabs";
import { PlaceholderCard } from "@/components/placeholder-card";

export default function DebugHttp() {
  const { t } = useTranslation();
  // 读取当前激活的子标签页（?tab= 查询参数），无命中时退回栏目名。
  const { activeTab } = useActivePageTab();

  return (
    <PageContainer>
      <PlaceholderCard title={t(activeTab?.labelKey ?? "nav.debugHttp")} />
    </PageContainer>
  );
}
