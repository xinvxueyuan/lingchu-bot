import type { Config } from "@react-router/dev/config";

export default {
  // SSR mode (default): the app is server-rendered at runtime by the Node
  // server. `build/server/index.js` is a Node-runnable application server,
  // while `build/client/` holds the static assets (JS/CSS, etc.).
  appDirectory: "src",
} satisfies Config;
