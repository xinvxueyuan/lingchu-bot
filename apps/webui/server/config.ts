import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = path.dirname(fileURLToPath(import.meta.url));

/**
 * 解析 build 产物路径，兼容两种运行布局：
 * - 编译产物：`dist/server/`（`pnpm build:server` 后 `node dist/server/index.js`）→ `../../build`
 * - 源码运行：`server/`（dev 插件经 Vite bundle 后动态 import）→ `../build`
 * 两者都不存在（dev 未构建）时回退 dist 布局路径（dev 下不参与页面服务，无副作用）。
 */

/**
 * 自仓库根目录向上不变的锚点文件：找到它即确定仓库根，从而定位根 `.env`。
 * 本模块既可能以源码 `server/` 运行（dev 插件经 Vite bundle），也可能以编译产物
 * `dist/server/` 运行（生产），两者到仓库根的层数不同，故用锚点文件而非相对层数。
 */
const REPO_ROOT_MARKER = "pnpm-workspace.yaml";

/** 向上查找包含锚点文件的仓库根目录（找不到返回 null）。 */
function findRepoRoot(startDir: string): string | null {
  let dir = startDir;
  for (let i = 0; i < 10; i += 1) {
    if (fs.existsSync(path.join(dir, REPO_ROOT_MARKER))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

/**
 * 解析 `.env` 文件（对齐 node `--env-file` 语义）：
 * - 忽略空行与 `#` 开头的注释行；
 * - 支持 `KEY=VALUE`、`export KEY=VALUE` 与单/双引号包裹的值；
 * - 未加引号的值取整行剩余内容（不做变量展开、不处理行内注释）。
 */
function parseDotEnv(content: string): Record<string, string> {
  const env: Record<string, string> = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const rest = line.startsWith("export ") ? line.slice("export ".length) : line;
    const eq = rest.indexOf("=");
    if (eq === -1) continue;
    const key = rest.slice(0, eq).trim();
    if (!key) continue;
    let value = rest.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
}

let rootEnvLoaded = false;

/**
 * 将仓库根目录 `.env` 合并进 `process.env`（幂等，仅填充缺失键，真实环境变量优先）。
 * 统一 dev / prod 的 env 来源，替代旧 `tsx watch --env-file=../../.env` 约定：
 * - dev：dev 插件经 Vite `configureServer` 在进程内加载后端，同样吃到根 .env；
 * - prod：`node dist/server/index.js` 直接运行，无需外部 `--env-file`，镜像内无 .env 时自然跳过。
 */
function loadRootEnv(): void {
  if (rootEnvLoaded) return;
  rootEnvLoaded = true;
  const repoRoot = findRepoRoot(currentDir);
  if (!repoRoot) return;
  const envFile = path.join(repoRoot, ".env");
  if (!fs.existsSync(envFile)) return;
  const env = parseDotEnv(fs.readFileSync(envFile, "utf8"));
  for (const [key, value] of Object.entries(env)) {
    if (!(key in process.env)) process.env[key] = value;
  }
}

loadRootEnv();
function resolveBuildPath(distRelative: string, srcRelative: string): string {
  const distPath = path.resolve(currentDir, distRelative);
  const srcPath = path.resolve(currentDir, srcRelative);
  return fs.existsSync(srcPath) ? srcPath : distPath;
}

/**
 * 解析 WebUI base path：确保以单个 `/` 开头，且不以 `/` 结尾。
 * 默认转发前缀为 `/lingchu-bot/webui/v1`。
 */
function normalizeBasePath(base: string | undefined): string {
  const raw = (base ?? "/lingchu-bot/webui/v1").trim();
  if (!raw) return "";
  const withLeading = raw.startsWith("/") ? raw : `/${raw}`;
  return withLeading.replace(/\/+$/, "") || "/";
}

/**
 * 解析 NoneBot 上游 base URL：去掉末尾的 `/`，便于与 base path 拼接。
 */
function normalizeBaseUrl(url: string | undefined): string {
  const raw = (url ?? "http://localhost:8080").trim();
  return raw.replace(/\/+$/, "");
}

/**
 * 解析嗅探端口列表：从 `LINGCHU_WEBUI_DISCOVER_PORTS` 按逗号 / 空格分割，
 * trim 后只保留纯数字端口。未设置或为空时默认 `["8080"]`。
 */
function parseDiscoverPorts(): string[] {
  const raw = process.env.LINGCHU_WEBUI_DISCOVER_PORTS;
  if (!raw) return ["8080"];
  const ports = raw
    .split(/[,\s]+/)
    .map((p) => p.trim())
    .filter((p) => /^\d+$/.test(p));
  return ports.length > 0 ? ports : ["8080"];
}

export const config = {
  /**
   * 监听端口（默认 4173）。
   * 使用独立变量 LINGCHU_WEBUI_PORT 而非共享的 PORT：根 .env 的 PORT=8080 属于 nonebot，
   * dev:server 通过 --env-file 加载根 .env 时不能让其劫持 WebUI 后端端口。
   */
  port: Number(process.env.LINGCHU_WEBUI_PORT ?? 4173),
  /**
   * 生产模式：仅当 `NODE_ENV === "production"` 时本服务承担页面（静态资源 + SSR）兜底。
   * dev 模式（`pnpm dev` = 单一 `react-router dev` 进程，dev 插件在进程内挂载后端）下
   * NODE_ENV 未显式设为 production → 纯 API 后端，页面由 Vite dev 渲染，
   * 因此开发时无需预先 `pnpm build`，`server/*` 变更经 watcher 自动重启 dev server。
   */
  productionMode: process.env.NODE_ENV === "production",
  /** NoneBot 上游 base URL */
  nonebotBaseUrl: normalizeBaseUrl(process.env.NONEBOT_BASE_URL),
  /** `NONEBOT_BASE_URL` 是否被显式设置：真 → 覆盖模式；假 → 嗅探模式 */
  nonebotBaseUrlExplicit: Boolean(process.env.NONEBOT_BASE_URL),
  /** 嗅探时探测的本地端口列表（解析自 `LINGCHU_WEBUI_DISCOVER_PORTS`） */
  discoverPorts: parseDiscoverPorts(),
  /** 转发到上游时的前缀路径 */
  webuiBasePath: normalizeBasePath(process.env.LINGCHU_WEBUI_BASE_PATH),
  /** JWT 签名密钥（HS256）。生产环境必须通过环境变量提供。 */
  jwtSecret:
    process.env.WEBUI_JWT_SECRET ?? "dev-only-insecure-secret-change-me",
  /** 已构建的 SPA 静态目录（build/client） */
  clientDir: resolveBuildPath("../../build/client", "../build/client"),
  /**
   * SSR 服务端构建入口（build/server/index.js，react-router build 的 named exports 模块）。
   * 消费方式：动态 `import(pathToFileURL(serverEntry).href)` 后交给
   * `createRequestHandler(build, "production")`。
   */
  serverEntry: resolveBuildPath(
    "../../build/server/index.js",
    "../build/server/index.js",
  ),
} as const;

export type AppConfig = typeof config;
