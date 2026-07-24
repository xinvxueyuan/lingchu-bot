import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  root: import.meta.dirname,
  oxc: false,
  plugins: [
    react(),
    {
      name: "css-ignore",
      transform(_code, id) {
        if (id.endsWith(".css")) return { code: "" };
        return;
      },
    },
  ],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
    onConsoleLog(log) {
      return !log.includes("act(");
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
});
