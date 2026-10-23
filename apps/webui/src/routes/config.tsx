import { useTranslation } from "react-i18next";

import { PageContainer } from "@/components/page-container";
import { PlaceholderCard } from "@/components/placeholder-card";

export default function Config() {
  const { t } = useTranslation();

  return (
    <PageContainer>
      <PlaceholderCard title={t("nav.config")} />
    </PageContainer>
  );
}
