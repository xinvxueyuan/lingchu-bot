/**
 * Unified site-level metadata utilities.
 *
 * All page/layout `metadata` exports in this app should compose with the
 * helpers defined here so that `metadataBase`, the default `title` template,
 * site-level `openGraph`/`twitter` cards, and `alternates` (RSS feeds,
 * canonical URLs, locale mappings) stay in sync.
 *
 * The site URL is resolved at build time from the `NEXT_PUBLIC_SITE_URL`
 * environment variable and falls back to the production deployment URL
 * declared in `SITE_URL`. This lets the same build pipeline serve a preview
 * environment without editing source code.
 */
import type { Metadata } from "next";
import { appName, SITE_URL } from "./shared";

const SITE_DESCRIPTION =
  "Lingchu Bot is a NoneBot2-based QQ group management bot with permission-aware commands and operator-focused documentation.";

const SITE_DESCRIPTION_ZH =
  "Lingchu Bot 是基于 NoneBot2 的 QQ 群管理机器人，提供权限感知命令与面向运营的文档。";

export function getSiteUrl(): URL {
  const raw = process.env["NEXT_PUBLIC_SITE_URL"]?.trim() || SITE_URL;
  // Ensure the pathname ends with `/` so `metadataBase` resolves
  // `openGraph.images` and similar relative URLs against the site root
  // (e.g. `/og/docs/...` -> `https://host/og/docs/...`).
  const normalized = /\/$/.test(raw) ? raw : `${raw}/`;
  return new URL(normalized);
}

export function getSiteUrlString(): string {
  return getSiteUrl().href.replace(/\/$/, "");
}

export function getSiteMetadata(): Metadata {
  const siteUrl = getSiteUrl();
  return {
    metadataBase: siteUrl,
    applicationName: appName,
    title: {
      default: appName,
      template: `%s | ${appName}`,
    },
    description: SITE_DESCRIPTION,
    openGraph: {
      type: "website",
      siteName: appName,
      title: appName,
      description: SITE_DESCRIPTION,
      url: siteUrl,
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title: appName,
      description: SITE_DESCRIPTION,
    },
  };
}

export function getSiteAlternatesTypes(): NonNullable<Metadata["alternates"]>["types"] {
  const base = getSiteUrlString();
  return {
    "application/rss+xml": [
      { title: `${appName} Docs`, url: `${base}/rss.xml` },
      { title: `${appName} 文档`, url: `${base}/zh/rss.xml` },
    ],
  };
}

const HOME_OG_IMAGE = "/opengraph-image";
const HOME_OG_IMAGE_ZH = "/zh/opengraph-image";

export function getHomeMetadata(locale: "en" | "zh"): Metadata {
  const isEn = locale === "en";
  return {
    title: isEn ? appName : `${appName} 文档`,
    description: isEn ? SITE_DESCRIPTION : SITE_DESCRIPTION_ZH,
    alternates: {
      canonical: isEn ? "/" : "/zh",
      languages: {
        en: "/",
        zh: "/zh",
        // x-default points at the en home (default locale per
        // `hideLocale: 'default-locale'`).
        "x-default": "/",
      },
      types: getSiteAlternatesTypes(),
    },
    openGraph: {
      type: "website",
      title: isEn ? appName : `${appName} 文档`,
      description: isEn ? SITE_DESCRIPTION : SITE_DESCRIPTION_ZH,
      url: isEn ? "/" : "/zh",
      siteName: appName,
      locale: isEn ? "en_US" : "zh_CN",
      images: isEn ? HOME_OG_IMAGE : HOME_OG_IMAGE_ZH,
    },
    twitter: {
      card: "summary_large_image",
      title: isEn ? appName : `${appName} 文档`,
      description: isEn ? SITE_DESCRIPTION : SITE_DESCRIPTION_ZH,
      images: isEn ? HOME_OG_IMAGE : HOME_OG_IMAGE_ZH,
    },
  };
}

type DocsPage = {
  url: string;
  data: {
    title: string;
    description?: string | undefined;
  };
};

type HrefLangMap = NonNullable<NonNullable<Metadata["alternates"]>["languages"]>;

export function getDocsPageMetadata(
  page: DocsPage,
  imageUrl?: string,
  alternateUrl?: string,
): Metadata {
  // Infer the current locale from the page URL convention
  // (`/zh/docs/...` is the only zh-prefixed path the source emits).
  const currentLocale: "en" | "zh" = page.url.startsWith("/zh/") ? "zh" : "en";
  const ogLocale: "en_US" | "zh_CN" = currentLocale === "en" ? "en_US" : "zh_CN";
  const otherLocale: "en" | "zh" = currentLocale === "en" ? "zh" : "en";

  const openGraph: NonNullable<Metadata["openGraph"]> = {
    type: "article",
    title: page.data.title,
    description: page.data.description,
    url: page.url,
    locale: ogLocale,
  };
  if (imageUrl) {
    openGraph.images = imageUrl;
  }

  const languages: HrefLangMap = {
    [currentLocale]: page.url,
  };
  if (alternateUrl) {
    languages[otherLocale] = alternateUrl;
    // x-default points at the en version (default locale) of the page.
    languages["x-default"] = currentLocale === "en" ? page.url : alternateUrl;
  }

  const twitter: NonNullable<Metadata["twitter"]> = {
    card: "summary_large_image",
    title: page.data.title,
    description: page.data.description,
  };
  if (imageUrl) {
    twitter.images = imageUrl;
  }

  return {
    title: page.data.title,
    description: page.data.description,
    alternates: {
      canonical: page.url,
      languages,
      types: getSiteAlternatesTypes(),
    },
    openGraph,
    twitter,
  };
}
