import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

import { webuiDevPlugin } from "./server/dev-plugin";

export default defineConfig({
  plugins: [tailwindcss(), reactRouter(), webuiDevPlugin()],
  resolve: {
    tsconfigPaths: true,
  },
});
