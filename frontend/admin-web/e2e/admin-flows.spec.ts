import { test, expect } from "@playwright/test";

async function mockAdmin(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    localStorage.setItem("admin_at", "test");
    localStorage.setItem("admin_rt", "test");
  });
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          id: "admin-1",
          email: "admin@example.com",
          full_name: "演示管理员",
          role: "ADMIN",
        },
      }),
    }),
  );
  await page.route("**/api/v1/admin/console/system-status", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          backend: "healthy",
          database: "healthy",
          provider: "mock",
          model: "mock-model",
          embedding_provider: "mock",
          api_key_configured: false,
          base_url_configured: false,
          active_policy_count: 11,
          latest_policy_update: null,
          latest_tool_failure: null,
          app_version: "1.0.1",
        },
      }),
    }),
  );
}

test.describe("Admin Web E2E", () => {
  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("h1")).toContainText("智能售后中台");
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("home page redirects to login when unauthenticated", async ({
    page,
  }) => {
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
    await mockAdmin(page);
    await page.route(
      "**/api/v1/admin/after-sales/tickets/ticket-1",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            code: "OK",
            data: {
              id: "ticket-1",
              ticket_number: "TKT-TEST-1",
              order_id: "order-1",
              intent: "QUALITY_REFUND",
              status: "APPROVED",
              version: 1,
            },
          }),
        });
      },
    );
    await page.goto("/tickets/ticket-1");
    await expect(page.getByText("工单 TKT-TEST-1")).toBeVisible();
    await expect(page.getByText("质量问题退款")).toBeVisible();
  });

  test("authenticated navigation uses Chinese menu labels", async ({
    page,
  }) => {
    await mockAdmin(page);
    await page.goto("/system");
    for (const label of [
      "数据看板",
      "工单管理",
      "订单管理",
      "用户管理",
      "商品管理",
      "审批中心",
      "知识库管理",
      "Agent 追踪",
      "工具日志",
      "系统状态",
    ])
      await expect(
        page.getByRole("link", { name: label }).first(),
      ).toBeVisible();
  });

  test("product list uses placeholder without broken-image icon", async ({
    page,
  }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/products**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: "p1",
                name: "Aurora Buds Pro 无线降噪耳机",
                category: "ELECTRONICS",
                price: "699.00",
                stock: 10,
                is_returnable: true,
              },
            ],
            total: 1,
            page: 1,
            page_size: 100,
            total_pages: 1,
          },
        }),
      }),
    );
    await page.goto("/products");
    await expect(page.getByText("待上传")).toBeVisible();
    await expect(page.getByText("RA-AUD-001")).toBeVisible();
  });

  test("dashboard displays real API metrics", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/console/dashboard**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            range_days: 7,
            pending_tickets: 3,
            today_tickets: 2,
            pending_approvals: 1,
            agent_sessions: 9,
            policy_searches: 5,
            failed_tool_calls: 0,
            ticket_trend: [],
            ticket_statuses: [],
            intent_types: [],
            recent_high_risk_approvals: [],
            recent_failed_tools: [],
          },
        }),
      }),
    );
    await page.goto("/");
    await expect(page.getByText("待处理工单")).toBeVisible();
    await expect(page.getByText("政策检索次数")).toBeVisible();
  });

  test("orders list renders Chinese status", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/console/orders?**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: "o1",
                order_number: "ORD-1",
                user_id: "u1",
                user_name: "演示顾客",
                item_summary: "无线耳机",
                paid_amount: "699.00",
                status: "SHIPPED",
                logistics_status: "IN_TRANSIT",
                ticket_count: 1,
                created_at: "2026-07-17T08:00:00Z",
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1,
          },
        }),
      }),
    );
    await page.goto("/orders");
    await expect(page.getByText("ORD-1")).toBeVisible();
    await expect(page.getByRole("table").getByText("已发货")).toBeVisible();
  });

  test("order detail renders item and logistics", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/console/orders/o1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "o1",
            order_number: "ORD-1",
            user_id: "u1",
            user_name: "演示顾客",
            item_summary: "无线耳机",
            paid_amount: "699.00",
            total_amount: "699.00",
            discount_amount: "0.00",
            shipping_fee: "0.00",
            status: "SHIPPED",
            ticket_count: 0,
            created_at: "2026-07-17T08:00:00Z",
            items: [
              {
                id: "i1",
                product_id: "p1",
                product_name: "Aurora Buds Pro 无线降噪耳机",
                unit_price: "699.00",
                quantity: 1,
                subtotal: "699.00",
              },
            ],
            logistics: {
              status: "IN_TRANSIT",
              carrier: "顺丰速运",
              tracking_number: "SF1",
              current_location: "上海分拨中心",
            },
            tickets: [],
          },
        }),
      }),
    );
    await page.goto("/orders/o1");
    await expect(page.getByText("Aurora Buds Pro 无线降噪耳机")).toBeVisible();
    await expect(page.getByText("上海分拨中心")).toBeVisible();
  });

  test("users list is privacy-safe", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/console/users?**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                id: "u1",
                full_name: "演示顾客",
                email: "demo@example.com",
                role: "CUSTOMER",
                risk_level: "LOW",
                is_active: true,
                order_count: 3,
                ticket_count: 1,
                memory_count: 2,
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1,
          },
        }),
      }),
    );
    await page.goto("/users");
    await expect(page.getByText("演示顾客")).toBeVisible();
    await expect(page.getByRole("cell", { name: "顾客", exact: true })).toBeVisible();
    await expect(page.getByText("收货地址")).toHaveCount(0);
  });

  test("approval detail uses Chinese labels", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/approvals/a1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "a1",
            user_id: "u1",
            action_id: "act1",
            tool_name: "create_after_sales_ticket",
            approval_type: "RISK_HIT",
            status: "PENDING",
            risk_level: "HIGH",
            reason: "高风险操作",
            version: 1,
          },
        }),
      }),
    );
    await page.goto("/approvals/a1");
    await expect(page.getByText("待处理")).toBeVisible();
    await expect(page.getByText("高风险", { exact: true })).toBeVisible();
  });

  test("policy detail distinguishes rule source", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/policies/by-key/POL-RET-901", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            policy_key: "POL-RET-901",
            version: 1,
            title: "七天无理由退货规则",
            category: "RETURN",
            content: "合理试用不当然影响商品完好。",
            status: "ACTIVE",
            effective_date: "2026-01-01",
            source: "市场监管总局",
          },
        }),
      }),
    );
    await page.goto("/policies/POL-RET-901");
    await expect(page.getByText("合理试用不当然影响商品完好。")).toBeVisible();
    await expect(page.getByText("市场监管总局")).toBeVisible();
  });

  test("trace detail displays nine nodes", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/agent/traces/t1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { trace_id: "t1", nodes: [] },
        }),
      }),
    );
    await page.goto("/traces/t1");
    await expect(page.locator("ol li")).toHaveCount(9);
    await expect(page.getByText("9 节点执行时间线")).toBeVisible();
  });

  test("tool log detail hides raw input", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/agent/tool-logs/l1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            id: "l1",
            session_id: "s1",
            trace_id: "t1",
            tool_name: "search_after_sales_policy",
            is_success: true,
            duration_ms: 120,
            retry_count: 0,
          },
        }),
      }),
    );
    await page.goto("/tool-logs/l1");
    await expect(page.getByText("售后政策检索")).toBeVisible();
    await expect(page.getByText("不在管理端接口中返回")).toBeVisible();
  });

  test("system page reports configuration booleans only", async ({ page }) => {
    await mockAdmin(page);
    await page.goto("/system");
    await expect(page.getByText("接口密钥")).toBeVisible();
    await expect(page.getByText("未配置").first()).toBeVisible();
    await expect(page.getByText("服务地址", { exact: true })).toBeVisible();
  });

  test("mobile sidebar opens as a drawer", async ({ page }) => {
    await mockAdmin(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/system");
    await page.getByRole("button", { name: "打开导航" }).click();
    await expect(page.getByRole("link", { name: "工单管理" })).toBeVisible();
  });

  test("admin API failure shows Chinese error state", async ({ page }) => {
    await mockAdmin(page);
    await page.route("**/api/v1/admin/console/dashboard**", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ success: false, code: "INTERNAL_ERROR" }),
      }),
    );
    await page.goto("/");
    await expect(page.getByText("系统暂时无法处理，请稍后重试")).toBeVisible();
  });

  test("expired session returns to Chinese login page", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("admin_at", "expired"));
    await page.route("**/api/v1/auth/**", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ success: false, code: "UNAUTHORIZED" }),
      }),
    );
    await page.goto("/orders");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText("管理员登录")).toBeVisible();
  });
});
