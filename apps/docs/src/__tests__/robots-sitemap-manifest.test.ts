import { afterEach, describe, it, expect, vi } from "vitest";

// Mock the source module so sitemap.ts can iterate over a stable page list
// without depending on the real MDX content loader.
vi.mock("@/lib/source", () => ({
  source: {
    getPages: vi.fn(() => [
      // en page with a zh counterpart
      {
        url: "/docs/user-guide/commands",
        slugs: ["user-guide", "commands"],
        locale: "en",
        data: {
          title: "Commands",
          description: "desc",
          lastModified: "2025-01-01",
        },
      },
      // en page without a zh counterpart
      {
        url: "/docs/developer-guide/architecture/introduction",
        slugs: ["developer-guide", "architecture", "introduction"],
        locale: "en",
        data: { title: "Introduction" },
      },
      // zh page whose en counterpart exists
      {
        url: "/zh/docs/user-guide/commands",
        slugs: ["user-guide", "commands"],
        locale: "zh",
        data: { title: "群管命令", lastModified: "2025-02-02" },
      },
    ]),
    getPage: vi.fn((slugs: string[], locale: "en" | "zh") => {
      if (locale === "en" && slugs.join("/") === "user-guide/commands") {
        return {
          url: "/docs/user-guide/commands",
          slugs,
          locale: "en",
          data: { title: "Commands" },
        };
      }
      return undefined;
    }),
  },
  getAlternateUrl: vi.fn((page: { slugs: string[]; locale: "en" | "zh" }) => {
    if (
      page.locale === "zh" &&
      page.slugs.join("/") === "user-guide/commands"
    ) {
      return "/docs/user-guide/commands";
    }
    if (
      page.locale === "en" &&
      page.slugs.join("/") === "user-guide/commands"
    ) {
      return "/zh/docs/user-guide/commands";
    }
    return undefined;
  }),
}));

import robots from "@/app/robots";
import sitemap from "@/app/sitemap";
import manifest from "@/app/manifest";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("app/robots", () => {
  it("allows all crawlers and points at the sitemap", () => {
    const out = robots();
    expect(out.rules).toEqual([{ userAgent: "*", allow: "/" }]);
    expect(out.sitemap).toBe("https://lingchu.zone.id/sitemap.xml");
  });

  it("honors NEXT_PUBLIC_SITE_URL when set", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://preview.example.com/");
    const out = robots();
    expect(out.sitemap).toBe("https://preview.example.com/sitemap.xml");
  });
});

describe("app/sitemap", () => {
  it("emits the two home entries first with full alternates", () => {
    const out = sitemap();
    const homes = out.slice(0, 2);
    expect(homes[0]?.url).toBe("https://lingchu.zone.id/");
    expect(homes[0]?.alternates?.languages).toEqual({
      en: "https://lingchu.zone.id/",
      zh: "https://lingchu.zone.id/zh",
    });
    expect(homes[1]?.url).toBe("https://lingchu.zone.id/zh");
  });

  it("emits one entry per docs page with the right URL prefix", () => {
    const out = sitemap();
    const urls = out.map((entry) => entry.url);
    expect(urls).toContain("https://lingchu.zone.id/docs/user-guide/commands");
    expect(urls).toContain(
      "https://lingchu.zone.id/zh/docs/user-guide/commands",
    );
    expect(urls).toContain(
      "https://lingchu.zone.id/docs/developer-guide/architecture/introduction",
    );
  });

  it("attaches alternates.languages to docs pages", () => {
    const out = sitemap();
    const en = out.find(
      (e) => e.url === "https://lingchu.zone.id/docs/user-guide/commands",
    );
    expect(en?.alternates?.languages).toEqual({
      en: "https://lingchu.zone.id/docs/user-guide/commands",
      zh: "https://lingchu.zone.id/zh/docs/user-guide/commands",
    });
    const zh = out.find(
      (e) => e.url === "https://lingchu.zone.id/zh/docs/user-guide/commands",
    );
    expect(zh?.alternates?.languages).toEqual({
      zh: "https://lingchu.zone.id/zh/docs/user-guide/commands",
      en: "https://lingchu.zone.id/docs/user-guide/commands",
    });
  });

  it("emits a single-locale alternate entry when no counterpart exists", () => {
    const out = sitemap();
    const orphan = out.find(
      (e) =>
        e.url ===
        "https://lingchu.zone.id/docs/developer-guide/architecture/introduction",
    );
    expect(orphan?.alternates?.languages).toEqual({
      en: "https://lingchu.zone.id/docs/developer-guide/architecture/introduction",
    });
  });

  it("parses lastModified into a Date instance when provided", () => {
    const out = sitemap();
    const en = out.find(
      (e) => e.url === "https://lingchu.zone.id/docs/user-guide/commands",
    );
    expect(en?.lastModified).toBeInstanceOf(Date);
    expect((en?.lastModified as Date).toISOString()).toBe(
      "2025-01-01T00:00:00.000Z",
    );
  });
});

describe("app/manifest", () => {
  it("exposes a PWA manifest with the expected static fields", () => {
    const out = manifest();
    expect(out.name).toBe("Lingchu Bot");
    expect(out.start_url).toBe("/");
    expect(out.display).toBe("standalone");
    expect(out.icons?.[0]?.src).toBe("/favicon.ico");
  });
});
