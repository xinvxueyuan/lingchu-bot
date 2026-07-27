import react from "@astrojs/react";
import starlight from "@astrojs/starlight";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

const githubBaseUrl =
  "https://github.com/xinvxueyuan/lingchu-bot/edit/main/apps/docs/src/content/docs/";

export default defineConfig({
  site: "https://lingchu.zone.id/",
  integrations: [
    react(),
    starlight({
      title: "Lingchu Bot",
      customCss: ["./src/styles/global.css"],
      defaultLocale: "root",
      head: [
        {
          tag: "meta",
          attrs: {
            name: "theme-color",
            media: "(prefers-color-scheme: light)",
            content: "#ffffff",
          },
        },
        {
          tag: "meta",
          attrs: {
            name: "theme-color",
            media: "(prefers-color-scheme: dark)",
            content: "#0b0e14",
          },
        },
        {
          tag: "link",
          attrs: {
            rel: "preconnect",
            href: "https://fonts.googleapis.com",
          },
        },
        {
          tag: "link",
          attrs: {
            rel: "preconnect",
            href: "https://fonts.gstatic.com",
            crossorigin: "",
          },
        },
        {
          tag: "link",
          attrs: {
            rel: "stylesheet",
            href: "https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap",
          },
        },
      ],
      editLink: {
        baseUrl: githubBaseUrl,
      },
      locales: {
        root: {
          label: "English",
          lang: "en",
        },
        zh: {
          label: "简体中文",
          lang: "zh-CN",
        },
      },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/xinvxueyuan/lingchu-bot",
        },
      ],
      sidebar: [
        {
          label: "User Guide",
          translations: { zh: "用户指南" },
          items: [
            { slug: "user-guide/overview" },
            { slug: "user-guide/quick-start" },
            { slug: "user-guide/commands" },
            {
              label: "Configuration",
              translations: { zh: "配置" },
              items: [
                { slug: "user-guide/configuration" },
                { slug: "user-guide/configuration/environment-variables" },
                { slug: "user-guide/configuration/adapter-selection" },
                { slug: "user-guide/configuration/superuser" },
                { slug: "user-guide/configuration/inbound-mcp-server" },
              ],
            },
            {
              label: "Deployment",
              translations: { zh: "部署" },
              items: [{ slug: "user-guide/deployment/tipo-llama-cpp" }],
            },
            { slug: "user-guide/troubleshooting" },
          ],
        },
        {
          label: "Platforms",
          translations: { zh: "平台" },
          items: [
            { slug: "platforms" },
            {
              label: "QQ Platform",
              translations: { zh: "QQ 平台" },
              items: [
                { slug: "platforms/qq/overview" },
                {
                  label: "Framework Integrations",
                  translations: { zh: "框架对接" },
                  items: [
                    { slug: "platforms/qq/frameworks" },
                    { slug: "platforms/qq/frameworks/napcat-docker" },
                    { slug: "platforms/qq/frameworks/snowluma-docker" },
                  ],
                },
                { slug: "platforms/qq/command-reference" },
                {
                  label: "OneBot V11",
                  translations: { zh: "OneBot V11" },
                  items: [
                    { slug: "platforms/qq/onebot-v11/overview" },
                    { slug: "platforms/qq/onebot-v11/default" },
                    { slug: "platforms/qq/onebot-v11/napcat" },
                  ],
                },
              ],
            },
            {
              label: "Telegram",
              translations: { zh: "Telegram" },
              items: [{ slug: "platforms/telegram/overview" }],
            },
          ],
        },
        {
          label: "Developer Guide",
          translations: { zh: "开发指南" },
          items: [
            {
              label: "Architecture",
              translations: { zh: "架构" },
              items: [
                { slug: "developer-guide/architecture/introduction" },
                { slug: "developer-guide/architecture/platform-registry" },
                { slug: "developer-guide/architecture/adapter-guide" },
                { slug: "developer-guide/architecture/permissions" },
                { slug: "developer-guide/architecture/storage-orm" },
                { slug: "developer-guide/architecture/message-store" },
                { slug: "developer-guide/architecture/llm-service" },
                { slug: "developer-guide/architecture/scheduler" },
                { slug: "developer-guide/architecture/i18n-runtime" },
                { slug: "developer-guide/architecture/runtime-hooks" },
                { slug: "developer-guide/architecture/api-audit" },
              ],
            },
            {
              label: "Engineering",
              translations: { zh: "工程" },
              items: [
                { slug: "developer-guide/engineering/workflow" },
                { slug: "developer-guide/engineering/commit-style" },
                { slug: "developer-guide/engineering/i18n" },
                { slug: "developer-guide/engineering/testing-ci" },
                { slug: "developer-guide/engineering/gitnexus" },
                { slug: "developer-guide/engineering/skills" },
                { slug: "developer-guide/engineering/project-policy" },
                { slug: "developer-guide/engineering/p5-shadcn-integration" },
                { slug: "developer-guide/engineering/view-transitions" },
              ],
            },
          ],
        },
      ],
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
    build: {
      chunkSizeWarningLimit: 1500,
    },
  },
});
