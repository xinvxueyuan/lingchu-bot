import { describe, it, expect, vi } from "vitest";

// Mock the collections/server module to avoid loading MDX files during tests
vi.mock("collections/server", () => ({
  docs: {
    toFumadocsSource: () => ({}),
  },
}));

import { getPageImage, getPageMarkdownUrl, getLLMText, source } from "@/lib/source";

type Page = (typeof source)["$inferPage"];

function mockPage(overrides: {
  locale?: string;
  slugs?: string[];
  url?: string;
  title?: string;
  text?: string;
}): Page {
  const {
    locale = "en",
    slugs = [],
    url = "/docs/test",
    title = "Test Page",
    text = "Test content",
  } = overrides;
  return {
    locale,
    slugs,
    url,
    data: {
      title,
      getText: async () => text,
    },
  } as unknown as Page;
}

describe("source utilities", () => {
  describe("getPageImage", () => {
    it("should generate correct en image URL structure", () => {
      const page = mockPage({ locale: "en", slugs: ["getting-started"] });
      const result = getPageImage(page);

      expect(result.url).toBe("/og/docs/getting-started/image.png");
      expect(result.segments).toEqual(["getting-started", "image.png"]);
    });

    it("should generate correct zh image URL structure", () => {
      const page = mockPage({ locale: "zh", slugs: ["getting-started"] });
      const result = getPageImage(page);

      expect(result.url).toBe("/og/docs/zh/getting-started/image.png");
      expect(result.segments).toEqual(["zh", "getting-started", "image.png"]);
    });

    it("should handle nested slugs", () => {
      const page = mockPage({
        locale: "en",
        slugs: ["developer-guide", "engineering", "commit-style"],
      });
      const result = getPageImage(page);

      expect(result.url).toBe("/og/docs/developer-guide/engineering/commit-style/image.png");
    });
  });

  describe("getPageMarkdownUrl", () => {
    it("should generate correct en markdown URL structure", () => {
      const page = mockPage({ locale: "en", slugs: ["getting-started"] });
      const result = getPageMarkdownUrl(page);

      expect(result.url).toBe("/llms.mdx/docs/getting-started/content.md");
    });

    it("should generate correct zh markdown URL structure", () => {
      const page = mockPage({ locale: "zh", slugs: ["getting-started"] });
      const result = getPageMarkdownUrl(page);

      expect(result.url).toBe("/llms.mdx/docs/zh/getting-started/content.md");
    });
  });

  describe("getLLMText", () => {
    it("should generate LLM text with title, url and processed content", async () => {
      const page = mockPage({
        locale: "en",
        slugs: ["getting-started"],
        url: "/docs/getting-started",
        title: "Getting Started",
        text: "Welcome to the guide.",
      });

      const result = await getLLMText(page);

      expect(result).toBe("# Getting Started (/docs/getting-started)\n\nWelcome to the guide.");
    });

    it("should handle empty content", async () => {
      const page = mockPage({
        url: "/docs/empty",
        title: "Empty Page",
        text: "",
      });

      const result = await getLLMText(page);

      expect(result).toBe("# Empty Page (/docs/empty)\n\n");
    });
  });
});
