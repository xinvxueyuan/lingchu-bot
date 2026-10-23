/**
 * WebUI oRPC 客户端（纯浏览器侧，无 Node 服务端）。
 *
 * 所有过程共享一个 {@link RPCLink}：
 * - URL 前缀由构建期注入的 `import.meta.env.BASE_URL` 推导（Vite 的 base，
 *   即 `VITE_WEBUI_BASE_PATH`），运行时不硬编码任何前缀；
 * - 会话凭证是 HttpOnly Cookie，浏览器自动携带，故只需 `credentials: "same-origin"`；
 * - 401 统一拦截：会话失效（过期 / 进程重启）后跳转登录页，避免每个调用点重复处理。
 */

import { createORPCClient } from "@orpc/client";
import { RPCLink } from "@orpc/client/fetch";
import { type ContractRouterClient, inferRPCMethodFromContractRouter } from "@orpc/contract";

import { contract } from "@/orpc/contract";

/** RPC 路由相对前缀：Python 侧 `WebuiUrls.rpc_root` 为 `{base}/v1/rpc`。 */
const RPC_PATH = "v1/rpc";

/**
 * 把 Vite 的 base 归一化为「无尾斜杠的绝对路径前缀」。
 *
 * `import.meta.env.BASE_URL` 恒以 `/` 结尾（`/`、`/lc/webui/`），而拼接 RPC 路径
 * 需要去掉尾斜杠；同时保留前导斜杠，保证同源绝对路径（而非相对当前路由）。
 *
 * @param base - Vite base，例如 `/lc/webui/`。
 * @returns 归一化前缀，例如 `/lc/webui`；base 为根时返回空串。
 */
export function normalizeBasePath(base: string): string {
  // 折叠重复斜杠（"//lc//webui//" → "/lc/webui"），否则会拼出 `//v1/rpc` 这类非法路径。
  const collapsed = base.trim().replace(/\/{2,}/g, "/").replace(/\/+$/, "");
  if (!collapsed || collapsed === "/") return "";
  return collapsed.startsWith("/") ? collapsed : `/${collapsed}`;
}

/**
 * 由 base 推导 RPC 端点 URL。导出为纯函数，便于单测直接断言。
 *
 * 前导斜杠始终保留（同源绝对路径），不受 {@link normalizeBasePath} 返回空串的影响。
 *
 * @param base - Vite base，例如 `/lc/webui/`。
 * @returns RPC 端点 URL，例如 `/lc/webui/v1/rpc`；base 为根时为 `/v1/rpc`。
 */
export function buildRpcUrl(base: string): string {
  return `${normalizeBasePath(base)}/${RPC_PATH}`;
}

/** 应用 base（无尾斜杠），供路由 basename / 登录跳转等复用。 */
export const APP_BASE_PATH: string = normalizeBasePath(import.meta.env.BASE_URL);

/** 登录页 URL（同源绝对路径）。 */
export const LOGIN_URL: string = `${APP_BASE_PATH}/login`;

/** 会话失效时跳转登录页；已在登录页则不再重复跳转。 */
function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname === LOGIN_URL) return;
  window.location.assign(LOGIN_URL);
}

/**
 * 包一层 fetch：命中 401 时先跳登录页再抛出，
 * 让调用方仍能按失败处理（登录页自身的 401 由登录表单消费，不应跳转）。
 */
const fetchWithAuthGuard: typeof fetch = async (input, init) => {
  const response = await fetch(input, init);
  if (response.status === 401 && typeof window !== "undefined") {
    // 登录接口自身的 401 是「口令错误」，由表单展示，不触发跳转。
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.endsWith("/auth/login")) redirectToLogin();
  }
  return response;
};

/**
 * 解析 RPCLink 使用端点 URL。
 *
 * `RPCLink` 内部用 `new URL(url)` 解析端点，**相对路径会直接抛
 * `TypeError: Failed to construct 'URL': Invalid URL`**（且发生在发出请求之前，
 * 表现为"网络错误"而无任何网络记录）。浏览器侧因此拼成绝对地址。
 *
 * 构建期预渲染没有 `window`，此时返回相对路径即可——预渲染不会发起任何 RPC。
 *
 * @returns 绝对 URL（浏览器）或相对路径（构建期）。
 */
function resolveRpcUrl(): string {
  const path = buildRpcUrl(import.meta.env.BASE_URL);
  if (typeof window === "undefined") return path;
  return new URL(path, window.location.origin).toString();
}

const link = new RPCLink({
  url: resolveRpcUrl(),
  // 方法取自契约的 route.method（auth 为 POST，其余为 GET），与 Python 侧注册一致。
  method: inferRPCMethodFromContractRouter(contract),
  fetch: fetchWithAuthGuard,
});

/** 类型化客户端：过程名、输入、输出均由契约推导。 */
export const client: ContractRouterClient<typeof contract> = createORPCClient(link);
