import { useTranslation } from "react-i18next";
import type { Route } from "./+types/config";

import { PageContainer } from "@/components/page-container";
import { PlaceholderCard } from "@/components/placeholder-card";
import { appPageMeta } from "@/lib/meta";

export function meta({}: Route.MetaArgs) {
  return appPageMeta();
}

export default function Config() {
  const { t } = useTranslation();

  return (
    <PageContainer>
      <PlaceholderCard title={t("nav.config")} />
    </PageContainer>
  );
}
