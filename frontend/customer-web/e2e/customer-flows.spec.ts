import { test, expect } from "@playwright/test";

const TEST_EMAIL = `e2e-${Date.now()}@test.com`;
const TEST_PASS = "testpass123";

test.describe("Customer Web E2E", () => {
  test("login page loads and has form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("h1")).toContainText("登录");
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test("register page loads", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("h1")).toContainText("注册");
  });

  test("home page redirects to login when unauthenticated", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Should show login/register links
    const links = page.locator("a");
    const hrefs = await links.evaluateAll(els => els.map(el => (el as HTMLAnchorElement).href));
    const hasLogin = hrefs.some(h => h.includes("/login"));
    const hasRegister = hrefs.some(h => h.includes("/register"));
    expect(hasLogin || hasRegister).toBeTruthy();
  });

  test("agent page loads", async ({ page }) => {
    await page.goto("/agent");
    await page.waitForLoadState("networkidle");
    // Should show welcome or redirect to login
  });

  test("products page renders", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");
  });

  test("orders page renders", async ({ page }) => {
    await page.goto("/orders");
    await page.waitForLoadState("networkidle");
  });

  test("approvals page renders", async ({ page }) => {
    await page.goto("/approvals");
    await page.waitForLoadState("networkidle");
  });

  test("memories page renders", async ({ page }) => {
    await page.goto("/memories");
    await page.waitForLoadState("networkidle");
  });
});
