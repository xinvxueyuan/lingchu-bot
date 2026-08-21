import { expect, test, type Page } from "@playwright/test";

// Collect browser-side errors (uncaught page errors + console.error messages)
// so the p5 island test can assert that mounting the canvas does not log any
// runtime errors. Returned array is captured by reference per page.
const collectErrors = (page: Page): string[] => {
  const errors: string[] = [];
  page.on("pageerror", (err) => {
    errors.push(`pageerror: ${err.message}`);
  });
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    errors.push(`console.error: ${msg.text()}`);
  });
  return errors;
};

test("p5 React island renders a canvas without console errors", async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto("/how-to/docs/p5-shadcn/");

  await expect(
    page.getByRole("heading", { level: 1, name: "p5.js & shadcn Integration" }),
  ).toBeVisible();

  await page.waitForSelector("canvas", { timeout: 10_000 });
  await expect(page.locator("canvas")).toBeVisible();

  expect(errors).toEqual([]);
});

test("home hero flow-field renders a canvas behind the hero content", async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto("/");

  // The hero banner wraps the canvas and the hero content.
  await expect(page.locator(".hero-banner")).toBeVisible();
  await expect(page.locator(".hero-banner .hero-title")).toBeVisible();
  await page.waitForSelector(".hero-banner canvas", { timeout: 10_000 });
  await expect(page.locator(".hero-banner canvas")).toBeVisible();

  expect(errors).toEqual([]);
});

test("shadcn dialog React island opens in MDX", async ({ page }) => {
  await page.goto("/how-to/docs/p5-shadcn/");

  await page.getByRole("button", { name: "Open Dialog" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Theme Bridge Works")).toBeVisible();
});

test("shadcn badge and alert render as static content in MDX", async ({ page }) => {
  await page.goto("/how-to/docs/p5-shadcn/");

  // Badge renders inline with a data-slot attribute.
  await expect(page.locator('[data-slot="badge"]').first()).toBeVisible();
  // Alert renders as a note region with a title. "Adapter selected" appears in
  // both the inline example and the BadgeAlertDemo, so scope to the first alert.
  await expect(page.locator('[data-slot="alert"]').first()).toBeVisible();
  await expect(page.locator('[data-slot="alert"]').first().getByText("Adapter selected")).toBeVisible();
});
