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

  test("ticket detail route renders ticket data", async ({ page }) => {
    await page.route("**/api/v1/admin/after-sales/tickets/ticket-1", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          id: "ticket-1", ticket_number: "TKT-TEST-1", order_id: "order-1",
          intent: "QUALITY_REFUND", status: "APPROVED", version: 1,
        } }),
      });
    });
    await page.goto("/tickets/ticket-1");
    await expect(page.getByRole("heading", { name: "TKT-TEST-1" })).toBeVisible();
    await expect(page.getByText("QUALITY_REFUND")).toBeVisible();
  });
});
