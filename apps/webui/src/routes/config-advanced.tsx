import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, RotateCcw } from "lucide-react";
import type { Route } from "./+types/config-advanced";

import { BoolSegment, ConfigForm } from "@/components/config-form";
import { PageContainer } from "@/components/page-container";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  getAdvancedConfig,
  saveAdvancedConfig,
  type AdvancedConfigData,
  type CommandConfig,
  type ConfigFieldSchema,
} from "@/lib/config-api";
import { appPageMeta } from "@/lib/meta";
import { cn } from "@/lib/utils";

export function meta({}: Route.MetaArgs) {
  return appPageMeta();
}

/** 加载失败引导（与错误风格一致的文案 + 重试按钮）。 */
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

/**
 * 单指令卡片：默认展开；头部为指令展示名 + enabled 开关；内容为
 * defaults 表单（按 schema）+ policies JSON 文本域，独立 PUT 保存。
 */
function CommandCard({
  commandKey,
  config,
  fields,
}: {
  commandKey: string;
  config: CommandConfig;
  fields: ConfigFieldSchema[];
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(true);
  const [enabled, setEnabled] = useState(config.enabled);

  // defaults 表单之外追加 policies（JSON 文本域）字段。
  const formFields = useMemo<ConfigFieldSchema[]>(
    () => [...fields, { key: "policies", type: "map" }],
    [fields],
  );
  const defaultKeys = fields.map((f) => f.key);

  const displayName = t(`config.commands.${commandKey}`, {
    defaultValue: commandKey,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{displayName}</CardTitle>
        <CardAction className="flex items-center gap-3">
          <span className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">{t("config.enabled")}</span>
            <BoolSegment
              size="sm"
              value={enabled}
              onChange={setEnabled}
              ariaLabel={t("config.enabled")}
            />
          </span>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={t(open ? "config.collapse" : "config.expand")}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <ChevronDown
              className={cn("size-4 transition-transform", !open && "-rotate-90")}
            />
          </button>
        </CardAction>
      </CardHeader>
      {open ? (
        <CardContent>
          <ConfigForm
            fields={formFields}
            values={{ ...config.defaults, policies: config.policies }}
            labelKeyPrefix={`config.fields.${commandKey}`}
            onSubmit={async (values) => {
              const defaults = Object.fromEntries(
                defaultKeys.map((k) => [k, values[k]]),
              );
              await saveAdvancedConfig(commandKey, {
                enabled,
                defaults,
                policies: values.policies as Record<string, unknown>,
              });
            }}
          />
        </CardContent>
      ) : null}
    </Card>
  );
}

export default function ConfigAdvanced() {
  const { t } = useTranslation();
  const [data, setData] = useState<AdvancedConfigData | null>(null);
  const [pending, setPending] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    setPending(true);
    setLoadError(false);
    try {
      setData(await getAdvancedConfig());
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
      <h1 className="mb-4 text-lg font-semibold">{t("nav.configAdvanced")}</h1>
      {pending ? (
        <p className="text-sm text-muted-foreground">{t("overview.loading")}</p>
      ) : loadError ? (
        <LoadError onRetry={() => void load()} />
      ) : data ? (
        <div className="grid gap-4">
          {Object.keys(data.commands).map((commandKey) => (
            <CommandCard
              key={commandKey}
              commandKey={commandKey}
              config={data.commands[commandKey]}
              fields={data.schema[commandKey] ?? []}
            />
          ))}
        </div>
      ) : null}
    </PageContainer>
  );
}