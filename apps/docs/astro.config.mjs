import react from "@astrojs/react";
import starlight from "@astrojs/starlight";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

const githubBaseUrl =
  "https://github.com/xinvxueyuan/lingchu-bot/edit/main/apps/docs/src/content/docs/";

// Diátaxis restructure: map legacy doc slugs to their new quadrant paths.
// Astro top-level `redirects` emits a meta-refresh page at each old URL so
// external links and bookmarks survive the information-architecture change.
// ZH mirrors are generated automatically under /zh/.
const docRedirectMap = {
  // Tutorials
  "/user-guide/quick-start": "/tutorials/getting-started",
  "/platforms/qq/onebot-v11/overview": "/tutorials/first-adapter",
  // How-to — Deployment
  "/user-guide/deployment/tipo-llama-cpp": "/how-to/deploy/tipo-llama-cpp",
  // How-to — Configuration
  "/user-guide/configuration/superuser": "/how-to/configure/superuser",
  "/user-guide/configuration/adapter-selection": "/how-to/configure/adapter",
  "/user-guide/configuration/inbound-mcp-server":
    "/how-to/configure/mcp-server",
  // How-to — Connect a Platform
  "/platforms/qq/onebot-v11/napcat": "/how-to/connect/qq-napcat",
  "/platforms/qq/frameworks/snowluma-docker": "/how-to/connect/qq-snowluma",
  "/platforms/telegram/overview": "/how-to/connect/telegram",
  // How-to — Troubleshooting
  "/user-guide/troubleshooting": "/how-to/troubleshoot",
  // How-to — Contributing
  "/developer-guide/engineering/commit-style": "/how-to/contribute/commits",
  "/developer-guide/engineering/i18n": "/how-to/contribute/i18n",
  "/developer-guide/engineering/testing-ci": "/how-to/contribute/testing",
  "/developer-guide/engineering/gitnexus": "/how-to/contribute/gitnexus",
  "/developer-guide/engineering/workflow": "/how-to/contribute/workflow",
  "/developer-guide/engineering/project-policy": "/how-to/contribute/workflow",
  "/developer-guide/engineering/skills": "/how-to/contribute/workflow",
  // How-to — Docs Engineering
  "/developer-guide/engineering/p5-shadcn-integration": "/how-to/docs/p5-shadcn",
  // Reference
  "/platforms/qq/command-reference": "/reference/commands",
  "/user-guide/configuration/environment-variables":
    "/reference/environment-variables",
  "/user-guide/configuration": "/reference/configuration",
  "/developer-guide/architecture/platform-registry":
    "/reference/platform-registry",
  "/developer-guide/architecture/permissions":
    "/reference/architecture/permissions",
  "/developer-guide/architecture/storage-orm":
    "/reference/architecture/storage-orm",
  "/developer-guide/architecture/message-store":
    "/reference/architecture/message-store",
  "/developer-guide/architecture/llm-service":
    "/reference/architecture/llm-service",
  "/developer-guide/architecture/scheduler": "/reference/architecture/scheduler",
  "/developer-guide/architecture/i18n-runtime":
    "/reference/architecture/i18n-runtime",
  "/developer-guide/architecture/runtime-hooks":
    "/reference/architecture/runtime-hooks",
  "/developer-guide/architecture/api-audit": "/reference/architecture/api-audit",
  "/developer-guide/architecture/adapter-guide":
    "/reference/architecture/adapter-system",
  // Explanation
  "/user-guide/overview": "/explanation/overview",
  "/platforms": "/explanation/platforms",
  "/developer-guide/architecture/introduction":
    "/explanation/architecture/introduction",
};

const docRedirects = {};
for (const [from, to] of Object.entries(docRedirectMap)) {
  docRedirects[from] = to;
  docRedirects[`/zh${from}`] = `/zh${to}`;
}

export default defineConfig({
  site: "https://lingchu.zone.id/",
  redirects: docRedirects,
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
          label: "Tutorials",
          translations: { zh: "教程" },
          items: [
            { slug: "tutorials/getting-started" },
            { slug: "tutorials/first-adapter" },
          ],
        },
        {
          label: "How-to Guides",
          translations: { zh: "操作指南" },
          items: [
            {
              label: "Deployment",
              translations: { zh: "部署" },
              items: [{ slug: "how-to/deploy/tipo-llama-cpp" }],
            },
            {
              label: "Configuration",
              translations: { zh: "配置" },
              items: [
                { slug: "how-to/configure/superuser" },
                { slug: "how-to/configure/adapter" },
                { slug: "how-to/configure/mcp-server" },
              ],
            },
            {
              label: "Connect a Platform",
              translations: { zh: "接入平台" },
              items: [
                { slug: "how-to/connect/qq-napcat" },
                { slug: "how-to/connect/qq-snowluma" },
                { slug: "how-to/connect/telegram" },
              ],
            },
            { slug: "how-to/troubleshoot" },
            {
              label: "Contributing",
              translations: { zh: "贡献" },
              items: [
                { slug: "how-to/contribute/workflow" },
                { slug: "how-to/contribute/commits" },
                { slug: "how-to/contribute/i18n" },
                { slug: "how-to/contribute/testing" },
                { slug: "how-to/contribute/gitnexus" },
              ],
            },
            {
              label: "Docs Engineering",
              translations: { zh: "文档工程" },
              items: [{ slug: "how-to/docs/p5-shadcn" }],
            },
          ],
        },
        {
          label: "Reference",
          translations: { zh: "参考" },
          items: [
            { slug: "reference/commands" },
            { slug: "reference/environment-variables" },
            { slug: "reference/configuration" },
            { slug: "reference/platform-registry" },
            {
              label: "Architecture",
              translations: { zh: "架构" },
              items: [
                { slug: "reference/architecture/adapter-system" },
                { slug: "reference/architecture/permissions" },
                { slug: "reference/architecture/storage-orm" },
                { slug: "reference/architecture/message-store" },
                { slug: "reference/architecture/llm-service" },
                { slug: "reference/architecture/scheduler" },
                { slug: "reference/architecture/i18n-runtime" },
                { slug: "reference/architecture/runtime-hooks" },
                { slug: "reference/architecture/api-audit" },
              ],
            },
          ],
        },
        {
          label: "Explanation",
          translations: { zh: "原理" },
          items: [
            { slug: "explanation/overview" },
            { slug: "explanation/platforms" },
            {
              label: "Architecture",
              translations: { zh: "架构" },
              items: [{ slug: "explanation/architecture/introduction" }],
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
