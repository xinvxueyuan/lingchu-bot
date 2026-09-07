import { type RouteConfig, index, layout, route } from "@react-router/dev/routes";

export default [
  layout("routes/_app.tsx", [
    index("routes/home.tsx"),
    route("config", "routes/config.tsx"),
    route("config/basic", "routes/config-basic.tsx"),
    route("config/advanced", "routes/config-advanced.tsx"),
    route("debug/http", "routes/debug-http.tsx"),
    route("debug/ws", "routes/debug-ws.tsx"),
  ]),
  route("login", "routes/login.tsx"),
] satisfies RouteConfig;
