import { expect, test } from "@playwright/test";

test("English docs root renders", async ({ page }) => {
  await page.goto("/");

  // The hero eyebrow carries the project name; the hero title is the H1.
  await expect(page.locator(".hero-eyebrow")).toContainText("Lingchu Bot");
  await expect(
    page.getByRole("heading", { level: 1, name: /NoneBot2 group-management bot/i }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quick navigation" })).toBeVisible();
  // "Quick Start" appears in both the hero actions and the card grid.
  await expect(page.getByRole("link", { name: "Quick Start" }).first()).toHaveAttribute(
    "href",
    "/tutorials/getting-started",
  );
});

test("Chinese docs root renders", async ({ page }) => {
  await page.goto("/zh/");

  await expect(page.locator(".hero-eyebrow")).toContainText("Lingchu Bot");
  await expect(
    page.getByRole("heading", { level: 1, name: /基于 NoneBot2 的群管理机器人/ }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "快速导航" })).toBeVisible();
  await expect(page.getByRole("link", { name: "快速开始" }).first()).toHaveAttribute(
    "href",
    "/zh/tutorials/getting-started",
  );
});

test("getting started page renders at the canonical URL", async ({ page }) => {
  await page.goto("/tutorials/getting-started");

  await expect(
    page.getByRole("heading", { level: 1, name: "Getting started with Lingchu Bot" }),
  ).toBeVisible();
});
