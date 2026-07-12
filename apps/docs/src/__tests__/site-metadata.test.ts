import { afterEach, describe, it, expect, vi } from "vitest";
import {
  getSiteAlternatesTypes,
  getSiteMetadata,
  getSiteUrl,
  getSiteUrlString,
  getHomeMetadata,
  getDocsPageMetadata,
} from "@/lib/site-metadata";
import { appName, SITE_URL } from "@/lib/shared";

const DEFAULT_ORIGIN = new URL(SITE_URL).origin;
const DEFAULT_BASE = SITE_URL.replace(/\/$/, "");

type RssFeed = { url: string; title?: string };

function getRssFeeds(types: unknown): RssFeed[] {
  const feeds = (types as Record<string, unknown> | undefined)?.["application/rss+xml"];
  if (!Array.isArray(feeds)) return [];
  return feeds.filter(
    (feed): feed is RssFeed =>
      typeof feed === "object" &&
      feed !== null &&
      "url" in feed &&
      typeof (feed as { url: unknown }).url === "string",
  );
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("site-metadata", () => {
  describe("getSiteUrl", () => {
    it("returns the production site URL by default", () => {
      const url = getSiteUrl();
      expect(url.origin).toBe(DEFAULT_ORIGIN);
      // Trailing slash on the pathname is required so `metadataBase`
      // resolves relative paths against the site root.
      expect(url.pathname).toBe("/");
    });

    it("honors NEXT_PUBLIC_SITE_URL when set", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com");
      const url = getSiteUrl();
      expect(url.origin).toBe("https://example.com");
      expect(url.pathname).toBe("/");
    });

    it("trims trailing slashes from NEXT_PUBLIC_SITE_URL", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com/");
      const url = getSiteUrl();
      expect(url.href).toBe("https://example.com/");
    });

    it("keeps the trailing slash so metadataBase resolves repo-relative paths", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com/sub");
      const url = getSiteUrl();
      expect(url.pathname).toBe("/sub/");
    });

    it("ignores whitespace-only NEXT_PUBLIC_SITE_URL", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", ' '.repeat(3));
      const url = getSiteUrl();
      expect(url.origin).toBe(DEFAULT_ORIGIN);
    });
  });

  describe("getSiteUrlString", () => {
    it("returns a string without trailing slash", () => {
      expect(getSiteUrlString()).toBe(DEFAULT_BASE);
    });

    it("returns a trimmed string when env is set", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com/");
      expect(getSiteUrlString()).toBe("https://example.com");
    });
  });

  describe("getSiteMetadata", () => {
    it("exposes metadataBase aligned with the site URL", () => {
      const meta = getSiteMetadata();
      expect(meta.metadataBase).toBeInstanceOf(URL);
      expect((meta.metadataBase as URL).origin).toBe(DEFAULT_ORIGIN);
    });

    it("defines a default title and template", () => {
      const meta = getSiteMetadata();
      expect(meta.title).toEqual({
        default: appName,
        template: `%s | ${appName}`,
      });
    });

    it("defines site-level openGraph and twitter cards", () => {
      const meta = getSiteMetadata();
      expect(meta.openGraph?.siteName).toBe(appName);
      // The returned object is the `OpenGraphWebsite` subtype (`type: 'website'`),
      // but `Metadata['openGraph']` is a union, so we narrow before reading the discriminator.
      expect((meta.openGraph as { type?: string } | undefined)?.type).toBe("website");
      expect((meta.twitter as { card?: string } | undefined)?.card).toBe("summary_large_image");
    });
  });

  describe("getSiteAlternatesTypes", () => {
    it("returns RSS feeds for both locales", () => {
      const types = getSiteAlternatesTypes();
      const feeds = (types?.["application/rss+xml"] ?? []) as Array<{
        url: string;
        title?: string;
      }>;
      expect(feeds).toHaveLength(2);
      expect(feeds[0]?.url).toBe(`${DEFAULT_BASE}/rss.xml`);
      expect(feeds[1]?.url).toBe(`${DEFAULT_BASE}/zh/rss.xml`);
    });

    it("uses NEXT_PUBLIC_SITE_URL when set", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com/");
      const types = getSiteAlternatesTypes();
      const feeds = (types?.["application/rss+xml"] ?? []) as Array<{
        url: string;
        title?: string;
      }>;
      expect(feeds[0]?.url).toBe("https://example.com/rss.xml");
    });
  });

  describe("getHomeMetadata", () => {
    it("returns canonical and language alternates for the en home", () => {
      const meta = getHomeMetadata("en");
      expect(meta.alternates?.canonical).toBe("/");
      expect(meta.alternates?.languages).toEqual({
        en: "/",
        zh: "/zh",
        "x-default": "/",
      });
    });

    it("returns canonical and language alternates for the zh home", () => {
      const meta = getHomeMetadata("zh");
      expect(meta.alternates?.canonical).toBe("/zh");
      expect(meta.alternates?.languages).toEqual({
        en: "/",
        zh: "/zh",
        "x-default": "/",
      });
    });

    it("uses the locale-specific title", () => {
      expect(getHomeMetadata("en").title).toBe(appName);
      expect(getHomeMetadata("zh").title).toBe(`${appName} 文档`);
    });

    it("embeds RSS alternates.types so the home page keeps the feed link", () => {
      const enTypes = getHomeMetadata("en").alternates?.types;
      const zhTypes = getHomeMetadata("zh").alternates?.types;
      expect(getRssFeeds(enTypes).length).toBeGreaterThan(0);
      expect(getRssFeeds(zhTypes).length).toBeGreaterThan(0);
    });

    it("declares openGraph.type=website and locale per locale", () => {
      const enMeta = getHomeMetadata("en");
      const zhMeta = getHomeMetadata("zh");
      expect((enMeta.openGraph as { type?: string } | undefined)?.type).toBe("website");
      expect((enMeta.openGraph as { locale?: string } | undefined)?.locale).toBe("en_US");
      expect((zhMeta.openGraph as { type?: string } | undefined)?.type).toBe("website");
      expect((zhMeta.openGraph as { locale?: string } | undefined)?.locale).toBe("zh_CN");
    });

    it("points openGraph.images and twitter.images at the locale home OG image", () => {
      const enMeta = getHomeMetadata("en");
      const zhMeta = getHomeMetadata("zh");
      expect(enMeta.openGraph?.images).toBe("/opengraph-image");
      expect((enMeta.twitter as { images?: unknown } | undefined)?.images).toBe("/opengraph-image");
      expect(zhMeta.openGraph?.images).toBe("/zh/opengraph-image");
      expect((zhMeta.twitter as { images?: unknown } | undefined)?.images).toBe(
        "/zh/opengraph-image",
      );
    });
  });

  describe("getDocsPageMetadata", () => {
    const enPage = {
      url: "/docs/user-guide/commands",
      data: {
        title: "Commands",
        description: "All available commands",
      },
    };

    it("maps page data into title/description and canonical URL", () => {
      const meta = getDocsPageMetadata(enPage);
      expect(meta.title).toBe("Commands");
      expect(meta.description).toBe("All available commands");
      expect(meta.alternates?.canonical).toBe("/docs/user-guide/commands");
    });

    it("includes openGraph url pointing at the page url", () => {
      const meta = getDocsPageMetadata(enPage);
      expect(meta.openGraph?.url).toBe("/docs/user-guide/commands");
    });

    it("sets openGraph.images when imageUrl is provided", () => {
      const meta = getDocsPageMetadata(enPage, "/og/docs/user-guide/commands/image.png");
      expect(meta.openGraph?.images).toBe("/og/docs/user-guide/commands/image.png");
    });

    it("omits openGraph.images when imageUrl is missing", () => {
      const meta = getDocsPageMetadata(enPage);
      expect(meta.openGraph?.images).toBeUndefined();
    });

    it("attaches a summary_large_image twitter card", () => {
      const meta = getDocsPageMetadata(enPage);
      expect((meta.twitter as { card?: string } | undefined)?.card).toBe("summary_large_image");
      expect(meta.twitter?.title).toBe("Commands");
    });

    it("declares openGraph.type=article and locale matching the inferred locale", () => {
      const enMeta = getDocsPageMetadata(enPage);
      expect((enMeta.openGraph as { type?: string } | undefined)?.type).toBe("article");
      expect((enMeta.openGraph as { locale?: string } | undefined)?.locale).toBe("en_US");

      const zhPage = {
        url: "/zh/docs/user-guide/commands",
        data: { title: "群管命令", description: "全部命令" },
      };
      const zhMeta = getDocsPageMetadata(zhPage);
      expect((zhMeta.openGraph as { type?: string } | undefined)?.type).toBe("article");
      expect((zhMeta.openGraph as { locale?: string } | undefined)?.locale).toBe("zh_CN");
    });

    it("mirrors imageUrl into twitter.images when provided", () => {
      const imageUrl = "/og/docs/user-guide/commands/image.png";
      const meta = getDocsPageMetadata(enPage, imageUrl);
      expect((meta.twitter as { images?: unknown } | undefined)?.images).toBe(imageUrl);
    });

    it("omits twitter.images when imageUrl is missing", () => {
      const meta = getDocsPageMetadata(enPage);
      expect((meta.twitter as { images?: unknown } | undefined)?.images).toBeUndefined();
    });

    it("infers en locale and emits only the current locale when no alternateUrl is given", () => {
      const meta = getDocsPageMetadata(enPage);
      const languages = meta.alternates?.languages as Record<string, string> | undefined;
      expect(languages).toEqual({ en: "/docs/user-guide/commands" });
      expect(languages?.["x-default"]).toBeUndefined();
      expect(languages?.["zh"]).toBeUndefined();
    });

    it("infers zh locale from a /zh/-prefixed page url when no alternateUrl is given", () => {
      const zhPage = {
        url: "/zh/docs/user-guide/commands",
        data: { title: "群管命令", description: "全部命令" },
      };
      const meta = getDocsPageMetadata(zhPage);
      const languages = meta.alternates?.languages as Record<string, string> | undefined;
      expect(languages).toEqual({ zh: "/zh/docs/user-guide/commands" });
      expect(languages?.["x-default"]).toBeUndefined();
    });

    it("emits en+zh+x-default hreflang when an alternateUrl is provided to an en page", () => {
      const meta = getDocsPageMetadata(enPage, undefined, "/zh/docs/user-guide/commands");
      const languages = meta.alternates?.languages as Record<string, string> | undefined;
      expect(languages).toEqual({
        en: "/docs/user-guide/commands",
        zh: "/zh/docs/user-guide/commands",
        "x-default": "/docs/user-guide/commands",
      });
    });

    it("emits en+zh+x-default with x-default pointing at the en alternate when given to a zh page", () => {
      const zhPage = {
        url: "/zh/docs/user-guide/commands",
        data: { title: "群管命令", description: "全部命令" },
      };
      const meta = getDocsPageMetadata(zhPage, undefined, "/docs/user-guide/commands");
      const languages = meta.alternates?.languages as Record<string, string> | undefined;
      expect(languages).toEqual({
        zh: "/zh/docs/user-guide/commands",
        en: "/docs/user-guide/commands",
        "x-default": "/docs/user-guide/commands",
      });
    });

    it("embeds RSS alternates.types so docs pages keep the feed link", () => {
      const enTypes = getDocsPageMetadata(enPage).alternates?.types;
      const zhTypes = getDocsPageMetadata({
        url: "/zh/docs/user-guide/commands",
        data: { title: "群管命令" },
      }).alternates?.types;
      expect(getRssFeeds(enTypes).length).toBeGreaterThan(0);
      expect(getRssFeeds(zhTypes).length).toBeGreaterThan(0);
    });
  });
});
