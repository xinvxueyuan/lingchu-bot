import { config } from "./config.js";
import { getCachedWebuiPassword } from "./password-cache.js";

export type DiscoveryStatus = "explicit" | "discovered" | "fallback";

/**
 * 模块级缓存的解析结果。
 * 初始值：显式设置时直接用 `config.nonebotBaseUrl`（explicit）；
 * 否则先以 `config.nonebotBaseUrl` 占位、状态 `fallback`，待启动时嗅探。
 */
let resolved: string = config.nonebotBaseUrl;
let status: DiscoveryStatus = config.nonebotBaseUrlExplicit
  ? "explicit"
  : "fallback";

/**
 * 解析 NoneBot 上游 base URL（进程内缓存）。
 *
 * - 显式设置 `NONEBOT_BASE_URL` → 直接返回，状态 `explicit`。
 * - 否则遍历 `discoverPorts`，对每个端口探测
 *   `http://127.0.0.1:{port}{webuiBasePath}/status`：
 *   响应 2xx 或 `401`（端点存在但密码保护）即视为命中，状态 `discovered`。
 * - 全部未命中 → 回退 `http://localhost:8080`，状态 `fallback`。
 */
export async function resolveNonebotBaseUrl(): Promise<string> {
  if (config.nonebotBaseUrlExplicit) {
    resolved = config.nonebotBaseUrl;
    status = "explicit";
    return resolved;
  }

  for (const port of config.discoverPorts) {
    const probe = `http://127.0.0.1:${port}${config.webuiBasePath}/status`;
    try {
      const res = await fetch(probe, {
        method: "GET",
        // 探测在登录前进行：缓存为空则带空密码头（端点 401 仍视为存在，可命中）。
        headers: { "X-Lingchu-Webui-Password": getCachedWebuiPassword() ?? "" },
        signal: AbortSignal.timeout(1500),
      });
      if (res.ok || res.status === 401) {
        resolved = `http://127.0.0.1:${port}`;
        status = "discovered";
        return resolved;
      }
    } catch {
      // 连接拒绝 / 超时等：继续下一个端口。
      continue;
    }
  }

  resolved = "http://localhost:8080";
  status = "fallback";
  return resolved;
}

/** 返回缓存的解析结果（proxy 转发使用）。 */
export function getResolvedNonebotBaseUrl(): string {
  return resolved;
}

/** 返回上游解析方式（index.ts 日志用）。 */
export function getDiscoveryStatus(): DiscoveryStatus {
  return status;
}
