/**
 * TOML 配置可视化管理 API 客户端（同源 /api 代理）。
 * 对应后端 services/webui 的 config 端点：
 * - GET/PUT /api/config/basic    → runtime-overrides.toml（MutableRuntimeSettings）
 * - GET/PUT /api/config/advanced → {command_key}.toml 指令配置
 * 端点返回「当前值 + 字段 schema」，前端按 schema 驱动渲染表单。
 * 非 2xx 收敛为携带后端 detail 的 ConfigApiError；401 走会话失效自愈。
 */

import { expireSession, getApiBase, getStoredToken } from "@/lib/api";

/** 配置字段渲染类型（与后端 schema 类型对齐）。 */
export type ConfigFieldType =
  | "boolean"
  | "integer"
  | "optional_integer"
  | "string"
  | "enum"
  | "map"
  | "boolean_or_map";

/** 单个配置字段的 schema 描述（后端返回）。 */
export type ConfigFieldSchema = {
  key: string;
  type: ConfigFieldType;
  /** 后端可选提供的标签；缺省时前端按 i18n 前缀解析。 */
  label?: string;
  /** 字段说明（可选）。 */
  description?: string;
  required?: boolean;
  /** integer / optional_integer 数值范围约束。 */
  min?: number;
  max?: number;
  /** enum 候选值。 */
  options?: string[];
};

/** 基本配置当前值（对应 MutableRuntimeSettings 字典）。 */
export type BasicConfigValues = {
  permission_platform_runtime_passthrough: boolean | Record<string, boolean>;
  command_trigger_overrides: Record<string, unknown>;
  menu_page_trigger_overrides: Record<string, unknown>;
};

/** GET /config/basic 响应：当前值 + 字段 schema。 */
export type BasicConfigData = {
  values: BasicConfigValues;
  schema: ConfigFieldSchema[];
};

/** 单指令配置（与 {command_key}.toml 结构一致）。 */
export type CommandConfig = {
  enabled: boolean;
  defaults: Record<string, unknown>;
  policies: Record<string, unknown>;
};

/** GET /config/advanced 响应：全部已注册指令 + 各自 defaults 字段 schema。 */
export type AdvancedConfigData = {
  commands: Record<string, CommandConfig>;
  schema: Record<string, ConfigFieldSchema[]>;
};

/** PUT /config/advanced 的 updates 载荷（enabled/defaults/policies 可部分提供）。 */
export type AdvancedConfigUpdates = {
  enabled?: boolean;
  defaults?: Record<string, unknown>;
  policies?: Record<string, unknown>;
};

/** 配置 API 失败：携带后端 detail 文案与 HTTP 状态。 */
export class ConfigApiError extends Error {
  readonly detail: string;
  readonly status: number;

  constructor(detail: string, status: number) {
    super(detail);
    this.name = "ConfigApiError";
    this.detail = detail;
    this.status = status;
  }
}

/** 统一请求：注入 Bearer 头、JSON 编解码、401 会话自愈、非 2xx 收敛为 ConfigApiError。 */
async function requestJson<T>(
  path: string,
  init?: { method?: string; body?: unknown },
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: string | undefined;
  if (init?.body !== undefined) {
    headers["content-type"] = "application/json";
    body = JSON.stringify(init.body);
  }
  const res = await fetch(`${getApiBase()}${path}`, {
    method: init?.method ?? "GET",
    headers,
    body,
  });
  if (res.status === 401) expireSession();
  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new ConfigApiError(data.detail ?? `request_failed: ${res.status}`, res.status);
  }
  return (await res.json()) as T;
}

/** 读取基本配置（runtime-overrides.toml）。 */
export async function getBasicConfig(): Promise<BasicConfigData> {
  return requestJson<BasicConfigData>("/config/basic");
}

/** 保存基本配置（全量覆盖 runtime-overrides.toml）。 */
export async function saveBasicConfig(settings: BasicConfigValues): Promise<void> {
  await requestJson<{ ok: boolean }>("/config/basic", { method: "PUT", body: { settings } });
}

/** 读取全部指令配置（{command_key}.toml）。 */
export async function getAdvancedConfig(): Promise<AdvancedConfigData> {
  return requestJson<AdvancedConfigData>("/config/advanced");
}

/** 保存单指令配置：updates 按 section 合并写回。 */
export async function saveAdvancedConfig(
  key: string,
  updates: AdvancedConfigUpdates,
): Promise<void> {
  await requestJson<{ ok: boolean }>("/config/advanced", {
    method: "PUT",
    body: { key, updates },
  });
}