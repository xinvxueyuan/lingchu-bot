import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

/**
 * Vitest 配置：只跑 `src/__tests__` 下的纯逻辑测试。
 *
 * 这里刻意不加载 `vite.config.ts`（其 `reactRouter()` 插件会接管模块解析并注入
 * 虚拟路由模块），因此 `@/` 别名需要单独声明，保持与 `tsconfig.json` 的 `paths` 一致。
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "~": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "node",
    include: ["src/__tests__/**/*.test.ts"],
  },
});
