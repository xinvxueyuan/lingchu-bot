/**
 * 路由配置（React Router framework 模式，SPA 构建）。
 *
 * `routes.ts` 由 react-router 的配置加载器在**构建期**读取，只接受"文件路径"
 * 形态的条目（`file` 字段）；传组件引用会让构建报
 * `Invalid key: Expected "file" but received undefined`。
 *
 * 根路由由 `root.tsx` 自动承担（`<html>/<head>/<body>`、`<Meta />`、`<Links />`、
 * `<Scripts />`、全局 Provider 与错误边界），因此这里不再声明额外的 layout。
 * 配合 `ssr: false`，构建期只把根路由预渲染为 `index.html`，其余路径交给客户端路由。
 */

import { type RouteConfig, index, layout, route } from "@react-router/dev/routes";

export default [
  layout("routes/_app.tsx", [
    index("routes/home.tsx"),
    route("config", "routes/config.tsx"),
    route("debug/http", "routes/debug-http.tsx"),
    route("debug/ws", "routes/debug-ws.tsx"),
  ]),
  route("login", "routes/login.tsx"),
] satisfies RouteConfig;
