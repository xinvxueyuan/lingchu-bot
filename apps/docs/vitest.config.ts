import path from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
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
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    onConsoleLog(log) {
      return !log.includes("act(");
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
      collections: path.resolve(import.meta.dirname, "./.source"),
    },
  },
});
