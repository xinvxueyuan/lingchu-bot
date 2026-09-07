import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { RotateCcw } from "lucide-react";
import type { Route } from "./+types/config-basic";

import { AsyncCard } from "@/components/async-card";
import { ConfigForm } from "@/components/config-form";
import { PageContainer } from "@/components/page-container";
import { Button } from "@/components/ui/button";
import {
  getBasicConfig,
  saveBasicConfig,
  type BasicConfigData,
  type BasicConfigValues,
} from "@/lib/config-api";
import { appPageMeta } from "@/lib/meta";

export function meta({}: Route.MetaArgs) {
  return appPageMeta();
}

/** 加载失败引导（与概览卡片错误风格一致）：错误文案 + 重试按钮。 */
function LoadError({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-2">
      <p role="alert" className="text-sm text-destructive">
        {t("config.loadError")}
      </p>
      <Button type="button" size="sm" variant="outline" className="w-fit" onClick={onRetry}>
        <RotateCcw className="size-3.5" />
        {t("config.retry")}
      </Button>
    </div>
  );
}

export default function ConfigBasic() {
  const { t } = useTranslation();
  const [data, setData] = useState<BasicConfigData | null>(null);
  const [pending, setPending] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    setPending(true);
    setLoadError(false);
    try {
      setData(await getBasicConfig());
    } catch {
      setLoadError(true);
    } finally {
      setPending(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <PageContainer>
      <AsyncCard
        title={t("nav.configBasic")}
        pending={pending}
        error={loadError ? <LoadError onRetry={() => void load()} /> : false}
      >
        {data ? (
          <ConfigForm
            fields={data.schema}
            values={data.values}
            onSubmit={async (values) => {
              await saveBasicConfig(values as BasicConfigValues);
            }}
          />
        ) : null}
      </AsyncCard>
    </PageContainer>
  );
}