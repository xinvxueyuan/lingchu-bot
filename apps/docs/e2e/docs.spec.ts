import { expect, test } from "@playwright/test";

test("English docs root renders", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Lingchu Bot" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quick navigation" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Quick Start" })).toHaveAttribute(
    "href",
    "/user-guide/quick-start/",
  );
});

test("Chinese docs root renders", async ({ page }) => {
  await page.goto("/zh/");

  await expect(page.getByRole("heading", { name: "Lingchu Bot" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "快速导航" })).toBeVisible();
  await expect(page.getByRole("link", { name: "快速开始" })).toHaveAttribute(
    "href",
    "/zh/user-guide/quick-start/",
  );
});

test("quick start page renders at the redesigned URL", async ({ page }) => {
  await page.goto("/user-guide/quick-start/");

  await expect(page.getByRole("heading", { level: 1, name: "Quick Start" })).toBeVisible();
});
