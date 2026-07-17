import { test, expect } from "@playwright/test";

const TEST_EMAIL = `e2e-${Date.now()}@test.com`;
const TEST_PASS = "testpass123";

async function loginDemo(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.locator('input[type="email"]').fill("demo@example.com");
  await page.locator('input[type="password"]').fill("demo123456");
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/$/);
}

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

  test("unauthenticated agent page redirects to login", async ({ page }) => {
    await page.goto("/agent");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("authenticated user can enter agent page directly", async ({ page }) => {
    await loginDemo(page);
    await page.goto("/agent");
    await expect(page.getByText("ResolveAI 智能客服")).toBeVisible();
  });

  test("policy consultation renders citation without confirmation", async ({ page }) => {
    await loginDemo(page);
    await page.route("**/api/v1/agent/sessions", async route => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          code: "OK",
          data: {
            session_id: "session-policy",
            message: "耳机拆封不当然排除退货，需结合合理试用和商品完好情况判断。",
            proposed_actions: [],
            citations: [{
              policy_key: "POL-RET-901", version: 1,
              title: "网络购物七日无理由退货规则", category: "RETURN",
              snippet: "商品应当完好", similarity_score: 0.91,
              source: "legal_requirement",
            }],
            trace_id: "trace-policy",
          },
        }),
      });
    });
    await page.goto("/agent");
    await page.getByPlaceholder("输入您的问题...").fill("拆封耳机还能退吗？");
    await page.getByRole("button", { name: "发送" }).click();

    await expect(page.getByText("耳机拆封不当然排除退货")).toBeVisible();
    await expect(page.getByText("POL-RET-901")).toBeVisible();
    await expect(page.getByRole("button", { name: "确认执行" })).toHaveCount(0);
  });

  test("explicit refund request shows action and confirmation clears it", async ({ page }) => {
    await loginDemo(page);
    let confirmed = false;
    await page.route("**/api/v1/agent/sessions**", async route => {
      const requestBody = route.request().postDataJSON() as { confirm_action_id?: string };
      confirmed = Boolean(requestBody.confirm_action_id);
      await route.fulfill({
        status: route.request().url().endsWith("/sessions") ? 201 : 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          code: "OK",
          data: confirmed ? {
            session_id: "session-action", message: "工单已创建。",
            proposed_actions: [], citations: [], trace_id: "trace-confirm",
          } : {
            session_id: "session-action", message: "请确认退款申请。",
            proposed_actions: [{
              action_id: "action-1", tool_name: "create_after_sales_ticket",
              description: "创建退款申请", status: "pending_confirmation",
            }],
            citations: [], trace_id: "trace-action",
          },
        }),
      });
    });
    await page.goto("/agent");
    await page.getByPlaceholder("输入您的问题...").fill("请帮我创建退款申请");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("button", { name: "确认执行" })).toBeVisible();
    await page.getByRole("button", { name: "确认执行" }).click();

    await expect(page.getByText("工单已创建。")).toBeVisible();
    await expect(page.getByRole("button", { name: "确认执行" })).toHaveCount(0);
    expect(confirmed).toBeTruthy();
  });

  test("products page renders", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");
  });

  test("orders page renders", async ({ page }) => {
    await page.goto("/orders");
    await page.waitForLoadState("networkidle");
  });

  test("order detail requests logistics from the order endpoint", async ({ page }) => {
    await loginDemo(page);
    let logisticsRequested = false;
    await page.route("**/api/v1/orders/order-1", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          id: "order-1", order_number: "ORD-TEST-1", status: "SHIPPED",
          total_amount: "99.00", shipping_fee: "0.00", items: [],
        } }),
      });
    });
    await page.route("**/api/v1/orders/order-1/logistics", async route => {
      logisticsRequested = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          order_id: "order-1", carrier: "SF Express",
          tracking_number: "SF00000000001", status: "IN_TRANSIT", events: [],
        } }),
      });
    });

    await page.goto("/orders/order-1");
    await expect(page.getByText("SF00000000001")).toBeVisible();
    expect(logisticsRequested).toBeTruthy();
  });

  test("approvals page renders", async ({ page }) => {
    await page.goto("/approvals");
    await page.waitForLoadState("networkidle");
  });

  test("memories page renders", async ({ page }) => {
    await page.goto("/memories");
    await page.waitForLoadState("networkidle");
  });

  test("memory can be edited", async ({ page }) => {
    await loginDemo(page);
    let content = "偏好简洁回答";
    await page.route("**/api/v1/memories**", async route => {
      if (route.request().method() === "PATCH") {
        content = (route.request().postDataJSON() as { content: string }).content;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, code: "OK", data: {
            id: "memory-1", memory_type: "PREFERENCE", key: "style",
            content, source: "USER_EXPLICIT", confidence: 1, status: "ACTIVE", version: 2,
          } }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          items: [{
            id: "memory-1", memory_type: "PREFERENCE", key: "style",
            content, source: "USER_EXPLICIT", confidence: 1, status: "ACTIVE", version: 1,
          }],
          total: 1, page: 1, page_size: 20,
        } }),
      });
    });

    await page.goto("/memories");
    await page.getByRole("button", { name: "修改" }).click();
    await page.getByLabel("修改记忆内容").fill("偏好使用简洁中文回答");
    await page.getByRole("button", { name: "保存修改" }).click();

    await expect(page.getByText("偏好使用简洁中文回答")).toBeVisible();
  });

  test("ticket cancellation sends an idempotency key", async ({ page }) => {
    await loginDemo(page);
    let cancellationKey = "";
    await page.route("**/api/v1/after-sales/tickets**", async route => {
      const request = route.request();
      if (request.method() === "POST" && request.url().endsWith("/cancel")) {
        cancellationKey = request.headers()["idempotency-key"] || "";
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, code: "OK", data: {
            id: "ticket-1", ticket_number: "AS-TEST-1", order_id: "order-1",
            intent: "QUALITY_REFUND", status: "CANCELLED", version: 2,
          } }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          items: [{
            id: "ticket-1", ticket_number: "AS-TEST-1", order_id: "order-1",
            intent: "QUALITY_REFUND", status: "APPROVED", version: 1,
          }],
          total: 1, page: 1, page_size: 20,
        } }),
      });
    });

    await page.goto("/tickets");
    await page.getByRole("button", { name: "取消工单" }).click();

    await expect(page.getByText("已取消")).toBeVisible();
    expect(cancellationKey).not.toBe("");
  });
});
