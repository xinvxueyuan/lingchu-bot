import type { MetadataRoute } from "next";
import { getAlternateUrl, source } from "@/lib/source";
import { getSiteUrlString } from "@/lib/site-metadata";

// `app/sitemap.ts` is a Next.js file convention that emits
// `out/sitemap.xml` at build time. We include both home pages and every
// docs page in every locale, with `alternates.languages` reflecting the
// cross-locale counterpart resolved via `getAlternateUrl`.

// `output: 'export'` requires the route to be statically generated.
export const dynamic = "force-static";
export const revalidate = false;

type Page = (typeof source)["$inferPage"];
type Locale = "en" | "zh";

function toAbsolute(base: string, url: string): string {
  return `${base}${url}`;
}

function buildAlternates(
  base: string,
  page: Page,
): NonNullable<MetadataRoute.Sitemap[number]["alternates"]> {
  const own = toAbsolute(base, page.url);
  const other = getAlternateUrl(page);
  // `page.locale` is typed as `string` on `$inferPage`, so narrow it to
  // the two-locale union before using it as a computed property key.
  const ownLocale: Locale = page.locale === "zh" ? "zh" : "en";
  if (!other) {
    return { languages: { [ownLocale]: own } };
  }
  const otherLocale: Locale = ownLocale === "zh" ? "en" : "zh";
  return {
    languages: {
      [ownLocale]: own,
      [otherLocale]: toAbsolute(base, other),
    },
  };
}

export default function sitemap(): MetadataRoute.Sitemap {
  const base = getSiteUrlString();
  const staticEntries: MetadataRoute.Sitemap = [
    {
      url: toAbsolute(base, "/"),
      changeFrequency: "weekly",
      priority: 1.0,
      alternates: {
        languages: { en: toAbsolute(base, "/"), zh: toAbsolute(base, "/zh") },
      },
    },
    {
      url: toAbsolute(base, "/zh"),
      changeFrequency: "weekly",
      priority: 1.0,
      alternates: {
        languages: { en: toAbsolute(base, "/"), zh: toAbsolute(base, "/zh") },
      },
    },
  ];

  const docsEntries: MetadataRoute.Sitemap = source.getPages().map((page) => {
    const lastModified = page.data.lastModified
      ? new Date(page.data.lastModified)
      : undefined;
    return {
      url: toAbsolute(base, page.url),
      lastModified,
      changeFrequency: "weekly",
      priority: 0.7,
      alternates: buildAlternates(base, page),
    };
  });

  return [...staticEntries, ...docsEntries];
}
