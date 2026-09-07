/**
 * schema 驱动的通用配置表单组件。
 *
 * 按后端字段 schema 渲染六类字段：
 * - boolean         → 开关（Button 分段：开/关）
 * - integer         → 数字输入（含 min/max 范围校验）
 * - optional_integer→ 数字输入，允许留空 → null
 * - string          → 文本输入
 * - enum            → 下拉选择（原生 select，styled）
 * - map             → JSON 文本域（提交前 JSON.parse 校验）
 * - boolean_or_map  → 全局开关 + 可切换「按平台映射」JSON 文本域
 *
 * 提交前做本地校验（必填 / 数值范围 / JSON 合法性），校验失败就地提示且不发起请求；
 * 保存按钮含 pending / 成功 / 失败态；空 schema 时展示空态文案。
 */

import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { CircleAlert, CircleCheck, CircleX } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ConfigApiError, type ConfigFieldSchema } from "@/lib/config-api";
import { cn } from "@/lib/utils";

/** boolean_or_map 字段的编辑器模型：全局开关 或 按平台映射 JSON。 */
export type BooleanOrMapEditor = {
  mode: "global" | "map";
  bool: boolean;
  /** map 模式下的 JSON 文本。 */
  json: string;
};

/** 字段编辑器内部值（map/boolean_or_map 在提交时才转换为实际值）。 */
type FieldEditorValue = string | number | boolean | BooleanOrMapEditor;

type SaveStatus = "idle" | "pending" | "success" | "error";

/** 布尔开关：Button 分段（开/关）。 */
export function BoolSegment({
  value,
  onChange,
  ariaLabel,
  size = "default",
}: {
  value: boolean;
  onChange: (next: boolean) => void;
  ariaLabel?: string;
  size?: "default" | "sm";
}) {
  const { t } = useTranslation();
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex items-center rounded-md border bg-background p-0.5",
        size === "sm" ? "h-8" : "h-9",
      )}
    >
      {[false, true].map((v) => (
        <button
          key={String(v)}
          type="button"
          aria-pressed={value === v}
          onClick={() => onChange(v)}
          className={cn(
            "rounded text-sm transition-colors",
            size === "sm" ? "px-2.5 py-0.5" : "px-3 py-1",
            value === v
              ? "bg-accent font-medium text-accent-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {t(v ? "config.bool.true" : "config.bool.false")}
        </button>
      ))}
    </div>
  );
}

/** map / boolean_or_map 的 JSON 文本域（等宽字体）。 */
function JsonTextarea({
  id,
  value,
  onChange,
}: {
  id: string;
  value: string;
  onChange: (next: string) => void;
}) {
  return (
    <textarea
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={6}
      spellCheck={false}
      placeholder="{}"
      className="min-h-28 w-full resize-y rounded-md border border-input bg-transparent px-3 py-2 font-mono text-sm shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30"
    />
  );
}

function ConfigForm({
  fields,
  values,
  onSubmit,
  submitLabel,
  labelKeyPrefix = "config.fields",
}: {
  fields: ConfigFieldSchema[];
  values: Record<string, unknown>;
  onSubmit: (values: Record<string, unknown>) => Promise<void>;
  /** 保存按钮文案；缺省为 t("config.save")。 */
  submitLabel?: string;
  /** 字段标签 i18n 前缀：基本页默认 "config.fields"；高级页传 "config.fields.<commandKey>"。 */
  labelKeyPrefix?: string;
}) {
  const { t, i18n } = useTranslation();
  const baseId = useId();

  /** 字段标签解析：后端 label > i18n（前缀 + 通用回退）> 字段 key。 */
  const resolveLabel = (field: ConfigFieldSchema): string => {
    if (field.label) return field.label;
    const candidates = [
      `${labelKeyPrefix}.${field.key}`,
      `config.fields.${field.key}`,
    ];
    for (const key of candidates) {
      if (i18n.exists(key)) return t(key);
    }
    return field.key;
  };

  /** enum 选项标签：i18n（config.enums.<fieldKey>.<option>）缺省时回落原始值。 */
  const resolveEnumLabel = (field: ConfigFieldSchema, option: string): string => {
    const key = `config.enums.${field.key}.${option}`;
    return i18n.exists(key) ? t(key) : option;
  };

  /** 由初始值构造字段编辑器值。 */
  const initEditorValue = (field: ConfigFieldSchema, value: unknown): FieldEditorValue => {
    switch (field.type) {
      case "boolean":
        return Boolean(value);
      case "integer":
      case "optional_integer":
        return value == null || value === "" ? "" : String(value);
      case "string":
      case "enum":
        return (value as string) ?? "";
      case "map":
        return JSON.stringify(value ?? {}, null, 2);
      case "boolean_or_map": {
        if (typeof value === "boolean") return { mode: "global", bool: value, json: "{}" };
        return { mode: "map", bool: true, json: JSON.stringify(value ?? {}, null, 2) };
      }
    }
  };

  const [form, setForm] = useState<Record<string, FieldEditorValue>>(() => {
    const initial: Record<string, FieldEditorValue> = {};
    for (const field of fields) {
      initial[field.key] = initEditorValue(field, values[field.key]);
    }
    return initial;
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    },
    [],
  );

  const updateValue = (key: string, next: FieldEditorValue) => {
    setForm((prev) => ({ ...prev, [key]: next }));
    // 有改动即复位保存状态，避免展示过期的成功/失败提示。
    setStatus("idle");
    setErrorDetail(null);
    setFieldErrors((prev) => {
      if (!(key in prev)) return prev;
      const nextErrors = { ...prev };
      delete nextErrors[key];
      return nextErrors;
    });
  };

  const isObjectJson = (text: string): boolean => {
    const parsed = JSON.parse(text) as unknown;
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed);
  };

  const validateField = (field: ConfigFieldSchema, editor: FieldEditorValue): string | null => {
    switch (field.type) {
      case "boolean":
      case "string":
      case "enum":
        if (field.required && (editor === "" || editor == null)) {
          return t("config.errors.required");
        }
        return null;
      case "integer":
      case "optional_integer": {
        if (editor === "") {
          if (field.type === "optional_integer") return null;
          return t("config.errors.integer");
        }
        const n = Number(editor);
        if (!Number.isInteger(n)) return t("config.errors.integer");
        if (field.min != null && field.max != null && (n < field.min || n > field.max)) {
          return t("config.errors.range", { min: field.min, max: field.max });
        }
        if (field.min != null && n < field.min) return t("config.errors.min", { min: field.min });
        if (field.max != null && n > field.max) return t("config.errors.max", { max: field.max });
        return null;
      }
      case "map": {
        try {
          return isObjectJson(editor as string) ? null : t("config.errors.jsonObject");
        } catch {
          return t("config.errors.json");
        }
      }
      case "boolean_or_map": {
        const { mode, json } = editor as BooleanOrMapEditor;
        if (mode === "global") return null;
        try {
          return isObjectJson(json) ? null : t("config.errors.jsonObject");
        } catch {
          return t("config.errors.json");
        }
      }
    }
  };

  const buildSubmitValues = (): Record<string, unknown> => {
    const result: Record<string, unknown> = {};
    for (const field of fields) {
      const editor = form[field.key];
      switch (field.type) {
        case "boolean":
          result[field.key] = Boolean(editor);
          break;
        case "integer":
        case "optional_integer":
          result[field.key] = editor === "" ? null : Number(editor);
          break;
        case "string":
        case "enum":
          result[field.key] = editor;
          break;
        case "map":
          result[field.key] = JSON.parse(editor as string) as unknown;
          break;
        case "boolean_or_map": {
          const { mode, bool, json } = editor as BooleanOrMapEditor;
          result[field.key] = mode === "global" ? bool : (JSON.parse(json) as unknown);
          break;
        }
      }
    }
    return result;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // 提交前本地校验：失败就地提示且不发起请求。
    const errors: Record<string, string> = {};
    for (const field of fields) {
      const err = validateField(field, form[field.key]);
      if (err) errors[field.key] = err;
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});
    setStatus("pending");
    setErrorDetail(null);
    try {
      await onSubmit(buildSubmitValues());
      setStatus("success");
      timerRef.current = window.setTimeout(
        () => setStatus((prev) => (prev === "success" ? "idle" : prev)),
        3000,
      );
    } catch (err) {
      setStatus("error");
      setErrorDetail(
        err instanceof ConfigApiError ? err.detail : t("config.saveFailed"),
      );
    }
  };

  if (fields.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("config.emptyState")}</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-5" noValidate>
      <div className="grid gap-4">
        {fields.map((field) => {
          const fieldId = `${baseId}-${field.key}`;
          const editor = form[field.key];
          const error = fieldErrors[field.key];
          return (
            <div key={field.key} className="grid gap-1.5">
              <Label className={cn(error && "text-destructive")}>{resolveLabel(field)}</Label>
              {field.type === "boolean" ? (
                <BoolSegment
                  value={Boolean(editor)}
                  onChange={(next) => updateValue(field.key, next)}
                  ariaLabel={resolveLabel(field)}
                />
              ) : field.type === "integer" || field.type === "optional_integer" ? (
                <Input
                  id={fieldId}
                  type="number"
                  inputMode="numeric"
                  value={editor as string}
                  onChange={(e) => updateValue(field.key, e.target.value)}
                  aria-invalid={Boolean(error)}
                  min={field.min}
                  max={field.max}
                  step={1}
                />
              ) : field.type === "string" ? (
                <Input
                  id={fieldId}
                  type="text"
                  value={editor as string}
                  onChange={(e) => updateValue(field.key, e.target.value)}
                  aria-invalid={Boolean(error)}
                />
              ) : field.type === "enum" ? (
                <select
                  id={fieldId}
                  value={editor as string}
                  onChange={(e) => updateValue(field.key, e.target.value)}
                  aria-invalid={Boolean(error)}
                  className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:bg-input/30"
                >
                  {(field.options ?? []).map((opt) => (
                    <option key={opt} value={opt}>
                      {resolveEnumLabel(field, opt)}
                    </option>
                  ))}
                </select>
              ) : field.type === "map" ? (
                <JsonTextarea
                  id={fieldId}
                  value={editor as string}
                  onChange={(next) => updateValue(field.key, next)}
                />
              ) : (
                (() => {
                  const { mode, bool, json } = editor as BooleanOrMapEditor;
                  return (
                    <div className="grid gap-2">
                      <div className="inline-flex w-fit items-center rounded-md border bg-background p-0.5">
                        {(["global", "map"] as const).map((m) => (
                          <button
                            key={m}
                            type="button"
                            aria-pressed={mode === m}
                            onClick={() =>
                              updateValue(field.key, { ...(editor as BooleanOrMapEditor), mode: m })
                            }
                            className={cn(
                              "rounded px-3 py-1 text-sm transition-colors",
                              mode === m
                                ? "bg-accent font-medium text-accent-foreground"
                                : "text-muted-foreground hover:text-foreground",
                            )}
                          >
                            {t(`config.boolOrMap.${m}`)}
                          </button>
                        ))}
                      </div>
                      {mode === "global" ? (
                        <BoolSegment
                          value={bool}
                          onChange={(next) =>
                            updateValue(field.key, { ...(editor as BooleanOrMapEditor), bool: next })
                          }
                          ariaLabel={resolveLabel(field)}
                        />
                      ) : (
                        <JsonTextarea
                          id={fieldId}
                          value={json}
                          onChange={(next) =>
                            updateValue(field.key, { ...(editor as BooleanOrMapEditor), json: next })
                          }
                        />
                      )}
                    </div>
                  );
                })()
              )}
              {field.description ? (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              ) : null}
              {error ? (
                <p role="alert" className="text-xs text-destructive">
                  {error}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={status === "pending"}>
          {status === "pending" ? t("config.saving") : (submitLabel ?? t("config.save"))}
        </Button>
        {status === "success" ? (
          <span className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
            <CircleCheck className="size-4" />
            {t("config.saveSuccess")}
          </span>
        ) : null}
        {status === "error" ? (
          <span role="alert" className="flex items-center gap-1.5 text-sm text-destructive">
            <CircleX className="size-4" />
            {errorDetail}
          </span>
        ) : null}
        {status === "pending" ? (
          <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <CircleAlert className="size-4" />
            {t("config.saving")}
          </span>
        ) : null}
      </div>
    </form>
  );
}

export { ConfigForm };