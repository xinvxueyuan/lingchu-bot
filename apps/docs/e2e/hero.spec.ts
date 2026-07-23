import { expect, test, type Page } from "@playwright/test";

// Collect browser-side errors (uncaught page errors + console.error messages)
// so each hero test can assert that mounting the p5 canvas does not log any
// runtime errors. Returned array is captured by reference per page.
//
// We filter out generic "Failed to load resource" 404 console messages because
// they are network-level prefetch failures (e.g. Next.js RSC `__next._tree.txt`
// prefetches that are absent from the static export), not JS runtime errors.
// The p5 library's own load path is already covered by the `canvas` visibility
// assertion below — if the p5 chunk failed to load, no canvas would render.
// Real JS errors (`pageerror`) and other console.error messages are kept.
const collectErrors = (page: Page): string[] => {
  const errors: string[] = [];
  page.on("pageerror", (err) => {
    errors.push(`pageerror: ${err.message}`);
  });
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (text.includes("Failed to load resource")) return;
    errors.push(`console.error: ${text}`);
  });
  return errors;
};

test("English home renders hero canvas without console errors", async ({
  page,
}) => {
  const errors = collectErrors(page);
  await page.goto("/");

  // Anchor on the hero heading before waiting for the dynamically-imported
  // sketch — confirms the page shell rendered and the canvas should follow.
  await expect(
    page.getByRole("heading", { name: "Lingchu Bot" }),
  ).toBeVisible();

  // HeroSketchLoader uses next/dynamic with ssr:false, so the canvas only
  // appears after hydration + the dynamic import resolves. 10s is generous
  // enough for cold dev/serve startup while still catching regressions.
  await page.waitForSelector("canvas", { timeout: 10_000 });
  await expect(page.locator("canvas")).toBeVisible();

  expect(errors).toEqual([]);
});

test("Chinese home renders hero canvas without console errors", async ({
  page,
}) => {
  const errors = collectErrors(page);
  await page.goto("/zh");

  await expect(
    page.getByRole("heading", { name: "Lingchu Bot 文档" }),
  ).toBeVisible();

  await page.waitForSelector("canvas", { timeout: 10_000 });
  await expect(page.locator("canvas")).toBeVisible();

  expect(errors).toEqual([]);
});
