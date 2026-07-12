import { expect, test } from "@playwright/test";

test("English home links to docs", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Lingchu Bot" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open docs" })).toHaveAttribute("href", "/docs");
});

test("Chinese home links to docs", async ({ page }) => {
  await page.goto("/zh");

  await expect(page.getByRole("heading", { name: "Lingchu Bot 文档" })).toBeVisible();
  await expect(page.getByRole("link", { name: "打开文档" })).toHaveAttribute("href", "/zh/docs");
});

test("docs index renders", async ({ page }) => {
  await page.goto("/docs");

  await expect(page.getByRole("heading", { name: "Project Introduction" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quick navigation" })).toBeVisible();
});
