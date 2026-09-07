import fs from "node:fs";
import { serve } from "@hono/node-server";

import { createWebuiApp, prepareWebuiRuntime } from "./app.js";
import { config } from "./config.js";
import {
  getDiscoveryStatus,
  getResolvedNonebotBaseUrl,
} from "./discover.js";

const app = createWebuiApp();

// 开发期使用默认密钥时给出安全提示。
if (config.jwtSecret === "dev-only-insecure-secret-change-me") {
  console.warn(
    "[webui] 警告：使用了默认开发 JWT 密钥，生产环境请通过环境变量 WEBUI_JWT_SECRET 配置强随机值。",
  );
}

// 提示 SSR 构建产物状态（build/client 静态目录 + build/server 服务端入口）。仅生产模式相关。
if (config.productionMode) {
  const missingArtifacts = [config.clientDir, config.serverEntry].filter(
    (p) => !fs.existsSync(p),
  );
  if (missingArtifacts.length > 0) {
    console.warn(
      `[webui] 未找到 SSR 构建产物：${missingArtifacts.join("、")}。请先运行 \`pnpm build\`（react-router build）。`,
    );
  }
}

// 启动前解析上游：显式设置则直接采用，否则在本地嗅探 nonebot。
await prepareWebuiRuntime();

serve({ fetch: app.fetch, port: config.port }, (info) => {
  console.log(`[webui] WebUI 运行时已启动： http://localhost:${info.port}`);

  const discoveryStatus = getDiscoveryStatus();
  const upstreamDesc =
    discoveryStatus === "explicit"
      ? "显式覆盖"
      : discoveryStatus === "discovered"
        ? "嗅探命中"
        : "回退(未自动发现)";
  console.log(
    `[webui] 转发上游： ${getResolvedNonebotBaseUrl() || "(未配置)"}  BASE_PATH=${config.webuiBasePath}  解析方式=${upstreamDesc}`,
  );

  // 回退场景：未在同机自动发现 nonebot，给出明确告警。
  if (discoveryStatus === "fallback") {
    console.warn(
      `[webui] 警告：未在同机自动发现 nonebot（已探测端口：${config.discoverPorts.join(", ")}），已回退到 http://localhost:8080。请确认 nonebot 已启动，或通过环境变量 NONEBOT_BASE_URL 显式指定上游地址。`,
    );
  }

  console.log(
    `[webui] 唯一密钥： 登录时经 ${getResolvedNonebotBaseUrl()}${config.webuiBasePath}/verify-password 校验（对比 .env 中 LINGCHU_WEBUI_PASSWORD），通过后内存缓存供转发使用`,
  );
});
