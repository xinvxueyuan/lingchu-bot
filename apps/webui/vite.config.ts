import path from "node:path";
import { fileURLToPath } from "node:url";

import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

/**
 * 开发期上游（NoneBot 同进程托管的 WebUI）：dev server 只渲染页面，
 * RPC 与静态资源请求转发到该地址。
 *
 * 生产前缀由 `react-router.config.ts` 的 `basename` 承担（`VITE_WEBUI_BASE_PATH`）；
 * 这里刻意不设 `base`，否则 SPA 模式的 fallback 预渲染会因资源路径被重写而失败。
 */
const upstream =
  process.env.LINGCHU_WEBUI_DEV_UPSTREAM ?? "http://127.0.0.1:8080";
const basePath = process.env.VITE_WEBUI_BASE_PATH ?? "/lc/webui/";
const normalizedBase = basePath.replace(/\/+$/, "") || "";
/** 资源 URL 前缀（带尾斜杠），必须与 `react-router.config.ts` 的 basename 一致。 */
const viteBase = `${normalizedBase}/`;

export default defineConfig({
  // 挂载前缀必须同时作用于 Vite 的 base 与 react-router 的 basename：
  // - base 决定 index.html 与 JS chunk 内部引用资源的 URL 前缀（JS 里同样硬编码，
  //   只改 index.html 会在浏览器里 404）；
  // - basename 必须与 base 完全一致（含尾斜杠），否则 SPA 模式在构建期的
  //   fallback 预渲染请求与路由表失配，报 "Received a 302 status code"。
  base: viteBase,
  plugins: [tailwindcss(), reactRouter()],
  resolve: {
    // `tsconfig.json` 的 `paths` 只作用于 TypeScript 类型解析，Vite/Rollup 打包时
    // 并不读取它。若不在此显式声明别名，`@/...` 导入会在 build 期报
    // "Cannot find module"，而 tsc 却能通过 —— 两边必须保持一致。
    alias: {
      "@": path.resolve(rootDir, "src"),
      "~": path.resolve(rootDir, "src"),
    },
  },
  server: {
    proxy: {
      // oRPC 过程：/lc/webui/v1/rpc/**（含登录、概览、只读透传）。
      [`${normalizedBase}/v1`]: { target: upstream, changeOrigin: true },
      // 静态资源：/lc/webui/assets/**。
      [`${normalizedBase}/assets`]: { target: upstream, changeOrigin: true },
    },
  },
});
