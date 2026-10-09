/**
 * 最小 WebUI API 客户端（同源 /api）。
 * 仅提供单用户登录与 UBT 存储所需的能力；更多端点按需扩展。
 */

const TOKEN_KEY = "lingchu-ubt";

/** WebUI 后端 API base：同源 /api（与后端 Hono 路由前缀一致）。 */
export function getApiBase(): string {
  return "/api";
}

/** 读取已存储的 UBT；非浏览器环境返回 null。 */
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** 保存 UBT。 */
export function setStoredToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

/** 清除 UBT（登出）。 */
export function clearStoredToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

/**
 * 会话失效自愈（如 dev / 生产进程重启后遗留的孤儿 UBT）：
 * 清除本地 UBT 并跳转登录页，等待用户重新登录恢复转发能力。
 */
export function expireSession(): void {
  clearStoredToken();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

/**
 * 登出：告知后端吊销当前 UBT（jti），并清除本地 token。
 * 无论服务端吊销是否成功，本地会话都会先行清除，保证界面即时退出。
 */
export async function authLogout(): Promise<void> {
  const token = getStoredToken();
  try {
    if (token) {
      await fetch(`${getApiBase()}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  } finally {
    clearStoredToken();
  }
}

/** 登录失败错误：携带后端错误码与 HTTP 状态。 */
export class LoginError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, status: number) {
    super(code);
    this.name = "LoginError";
    this.code = code;
    this.status = status;
  }
}

/**
 * 登录（单用户 root）：提交口令，成功返回 UBT。
 * @throws {LoginError} 请求失败（401 = 口令错误，其余为服务端/网络错误）。
 */
export async function authLogin(password: string): Promise<string> {
  const res = await fetch(`${getApiBase()}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as { error?: string };
    throw new LoginError(data.error ?? "login_failed", res.status);
  }
  const data = (await res.json()) as { token?: string };
  if (!data.token) throw new LoginError("login_failed", res.status);
  return data.token;
}
