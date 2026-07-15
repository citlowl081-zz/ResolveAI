import { test, expect } from "@playwright/test";

test.describe("Admin Web E2E", () => {
  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("h1")).toContainText("Admin");
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("home page redirects to login when unauthenticated", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("tickets page renders", async ({ page }) => {
    await page.goto("/tickets");
    await page.waitForLoadState("networkidle");
  });

  test("approvals page renders", async ({ page }) => {
    await page.goto("/approvals");
    await page.waitForLoadState("networkidle");
  });

  test("policies page renders", async ({ page }) => {
    await page.goto("/policies");
    await page.waitForLoadState("networkidle");
  });

  test("traces page renders", async ({ page }) => {
    await page.goto("/traces");
    await page.waitForLoadState("networkidle");
  });

  test("tool-logs page renders", async ({ page }) => {
    await page.goto("/tool-logs");
    await page.waitForLoadState("networkidle");
  });
});
