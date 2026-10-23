import type { Config } from "@react-router/dev/config";

/**
 * WebUI 构建配置：**纯静态 SPA**（`ssr: false`），没有 Node 服务端。
 *
 * 产物 `dist/client/` 由 Python（NoneBot 同进程）托管在可配置前缀下，默认
 * `/lc/webui`（见 `services/webui/paths.py`）。
 *
 * **挂载前缀只在这里声明，不要在 Vite 里再设 `base`**（实测组合）：
 * SPA 模式构建期会向预览服务器请求 `http://localhost${basename}` 生成 fallback HTML。
 * - `base: "/lc/webui/"` + `basename: "/"` → 预览服务器把 `/` 302 重定向到 base 前缀，
 *   构建以 `SPA Mode: Received a 302 status code from entry.server.tsx` 失败；
 * - `base` 不设（默认 `/`）+ `basename: "/lc/webui/"` → 通过。
 *
 * 前缀只为 dev server 与产物内的相对资源服务；`index.html` 以相对路径引用
 * `assets/...`，因此在任意前缀下都能正确解析。
 */
const base = process.env.VITE_WEBUI_BASE_PATH ?? "/lc/webui/";

export default {
  appDirectory: "src",
  // 关闭运行时服务端渲染：构建期仅预渲染根路由为 index.html，其余路径由 SPA 接管。
  ssr: false,
  // 产物目录从默认的 build/ 改为 dist/，与仓库既定产物路径 dist/client 对齐。
  buildDirectory: "dist",
  // 挂载前缀（含尾斜杠，与 Python 侧 `WebuiUrls.page_root` 一致）。
  basename: base,
} satisfies Config;
