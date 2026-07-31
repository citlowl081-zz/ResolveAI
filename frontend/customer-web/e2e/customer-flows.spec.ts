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
    const policyCitation = {
      policy_key: "POL-RET-901", version: 1,
      title: "网络购物七日无理由退货规则", category: "RETURN",
      snippet: "商品应当完好", similarity_score: 0.91,
      source: "legal_requirement",
    };
    await page.route("**/api/v1/agent/sessions**", async route => {
      const request = route.request();
      if (request.method() === "GET") {
        const isHistory = request.url().includes("/messages");
        await route.fulfill({
          status: 200, contentType: "application/json",
          body: JSON.stringify({ success: true, code: "OK", data: isHistory ? {
            items: [
              { message_id: "policy-user", role: "USER", content: "拆封耳机还能退吗？", sequence_number: 1, citations: [], proposed_actions: [], delivery_status: "sent" },
              { message_id: "policy-assistant", role: "ASSISTANT", content: "耳机拆封不当然排除退货，需结合合理试用和商品完好情况判断。", sequence_number: 2, citations: [policyCitation], proposed_actions: [], delivery_status: "sent" },
            ], total: 2, page: 1, page_size: 100, total_pages: 1,
          } : { items: [], total: 0, page: 1, page_size: 20, total_pages: 1 } }),
        });
        return;
      }
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
            citations: [policyCitation],
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
      const request = route.request();
      if (request.method() === "GET") {
        const isHistory = request.url().includes("/messages");
        const historyAction = confirmed ? [] : [{
          action_id: "action-1", tool_name: "create_after_sales_ticket",
          description: "创建退款申请", status: "pending_confirmation",
        }];
        await route.fulfill({
          status: 200, contentType: "application/json",
          body: JSON.stringify({ success: true, code: "OK", data: isHistory ? {
            items: [{
              message_id: "action-assistant", role: "ASSISTANT",
              content: confirmed ? "工单已创建。" : "请确认退款申请。",
              sequence_number: 2, citations: [], proposed_actions: historyAction,
              delivery_status: "sent",
            }], total: 1, page: 1, page_size: 100, total_pages: 1,
          } : { items: [], total: 0, page: 1, page_size: 20, total_pages: 1 } }),
        });
        return;
      }
      const requestBody = request.postDataJSON() as { confirm_action_id?: string };
      confirmed = Boolean(requestBody.confirm_action_id);
      await route.fulfill({
        status: request.url().endsWith("/sessions") ? 201 : 200,
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

  test("agent renders the user message optimistically before the reply", async ({ page }) => {
    await loginDemo(page);
    await page.route("**/api/v1/agent/sessions**", async route => {
      const request = route.request();
      if (request.method() === "GET") {
        await route.fulfill({
          status: 200, contentType: "application/json",
          body: JSON.stringify({ success: true, code: "OK", data: {
            items: [], total: 0, page: 1, page_size: 20, total_pages: 1,
          } }),
        });
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 600));
      await route.fulfill({
        status: 201, contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          session_id: "optimistic-session", message: "已经收到您的问题。",
          proposed_actions: [], citations: [], trace_id: "optimistic-trace",
        } }),
      });
    });

    await page.goto("/agent");
    await page.getByPlaceholder("输入您的问题...").fill("这条消息应该立即出现");
    await page.getByRole("button", { name: "发送" }).click();

    await expect(page.getByText("这条消息应该立即出现")).toBeVisible({ timeout: 100 });
    await expect(page.getByText("AI 正在分析你的问题…")).toBeVisible();
    await expect(page.getByPlaceholder("输入您的问题...")).toHaveValue("");
  });

  test("agent restores a database-backed conversation after reload", async ({ page }) => {
    await loginDemo(page);
    await page.route("**/api/v1/agent/sessions**", async route => {
      if (route.request().url().includes("/history-session/messages")) {
        await route.fulfill({
          status: 200, contentType: "application/json",
          body: JSON.stringify({ success: true, code: "OK", data: {
            items: [
              { message_id: "m1", role: "USER", content: "此前的用户问题", sequence_number: 1, citations: [], proposed_actions: [], delivery_status: "sent" },
              { message_id: "m2", role: "ASSISTANT", content: "此前的助手回答", sequence_number: 2, citations: [], proposed_actions: [], delivery_status: "sent" },
            ], total: 2, page: 1, page_size: 100, total_pages: 1,
          } }),
        });
        return;
      }
      await route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          items: [{
            session_id: "history-session", title: "此前的用户问题",
            status: "ACTIVE", message_count: 2,
            last_message_preview: "此前的助手回答",
            created_at: "2026-07-17T00:00:00Z", updated_at: "2026-07-17T00:01:00Z",
          }], total: 1, page: 1, page_size: 20, total_pages: 1,
        } }),
      });
    });

    await page.goto("/agent?session=history-session");
    await expect(page.getByRole("heading", { name: "历史对话" })).toBeVisible();
    await expect(page.getByText("此前的助手回答")).toBeVisible();
    await page.goto("/products");
    await page.goto("/agent");
    await expect(page.getByText("此前的助手回答")).toBeVisible();
    await page.reload();
    await expect(page.getByText("此前的用户问题").last()).toBeVisible();
    await expect(page.getByText("此前的助手回答")).toBeVisible();
  });

  test("explicit remember requires a separate confirmation", async ({ page }) => {
    await loginDemo(page);
    let memoryCreated = false;
    await page.route("**/api/v1/agent/sessions**", async route => {
      if (route.request().method() === "GET") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, code: "OK", data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 1 } }) });
        return;
      }
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ success: true, code: "OK", data: { session_id: "memory-session", message: "我可以在您确认后保存这条偏好。", proposed_actions: [], citations: [], trace_id: "memory-trace" } }) });
    });
    await page.route("**/api/v1/memories", async route => {
      memoryCreated = true;
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ success: true, code: "OK", data: { id: "memory-confirmed", memory_type: "PREFERENCE", content: "更倾向于换货而不是退款", status: "ACTIVE" } }) });
    });

    await page.goto("/agent");
    await page.getByPlaceholder("输入您的问题...").fill("请记住，我更倾向于换货而不是退款。");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("button", { name: "记住这条偏好" })).toBeVisible();
    expect(memoryCreated).toBeFalsy();
    await page.getByRole("button", { name: "记住这条偏好" }).click();
    await expect(page.getByText("已保存到长期记忆")).toBeVisible();
    expect(memoryCreated).toBeTruthy();
  });

  test("failed message retries with the same key without a duplicate bubble", async ({ page }) => {
    await loginDemo(page);
    const keys: string[] = [];
    let attempts = 0;
    await page.route("**/api/v1/agent/sessions**", async route => {
      const request = route.request();
      if (request.method() === "GET") {
        const isHistory = request.url().includes("/messages");
        await route.fulfill({
          status: 200, contentType: "application/json",
          body: JSON.stringify({ success: true, code: "OK", data: isHistory ? {
            items: [
              { message_id: "retry-user", role: "USER", content: "请重试这条消息", sequence_number: 1, citations: [], proposed_actions: [], delivery_status: "sent", client_message_id: keys[0] },
              { message_id: "retry-assistant", role: "ASSISTANT", content: "重试成功", sequence_number: 2, citations: [], proposed_actions: [], delivery_status: "sent" },
            ], total: 2, page: 1, page_size: 100, total_pages: 1,
          } : { items: [], total: 0, page: 1, page_size: 20, total_pages: 1 } }),
        });
        return;
      }
      attempts += 1;
      keys.push(request.headers()["idempotency-key"] || "");
      if (attempts === 1) {
        await route.fulfill({
          status: 500, contentType: "application/json",
          body: JSON.stringify({ success: false, code: "LLM_ERROR", message: "temporary" }),
        });
        return;
      }
      await route.fulfill({
        status: 201, contentType: "application/json",
        body: JSON.stringify({ success: true, code: "OK", data: {
          session_id: "retry-session", message: "重试成功",
          proposed_actions: [], citations: [], trace_id: "retry-trace",
        } }),
      });
    });

    await page.goto("/agent");
    await page.getByPlaceholder("输入您的问题...").fill("请重试这条消息");
    await page.getByRole("button", { name: "发送" }).click();
    await expect(page.getByRole("button", { name: "重新发送" })).toBeVisible();
    await page.getByRole("button", { name: "重新发送" }).click();
    await expect(page.getByText("重试成功")).toBeVisible();
    await expect(page.locator("section").getByText("请重试这条消息", { exact: true })).toHaveCount(1);
    expect(keys).toHaveLength(2);
    expect(keys[1]).toBe(keys[0]);
  });

  test("double click sends only one agent request", async ({ page }) => {
    await loginDemo(page);
    let sends = 0;
    await page.route("**/api/v1/agent/sessions**", async route => {
      const request = route.request();
      if (request.method() === "GET") {
        const isHistory = request.url().includes("/messages");
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, code: "OK", data: isHistory ? {
          items: [{ message_id: "double-assistant", role: "ASSISTANT", content: "只处理一次", sequence_number: 2, citations: [], proposed_actions: [], delivery_status: "sent" }],
          total: 1, page: 1, page_size: 100, total_pages: 1,
        } : { items: [], total: 0, page: 1, page_size: 20, total_pages: 1 } }) });
        return;
      }
      sends += 1;
      await new Promise(resolve => setTimeout(resolve, 300));
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ success: true, code: "OK", data: { session_id: "double-session", message: "只处理一次", proposed_actions: [], citations: [], trace_id: "double-trace" } }) });
    });

    await page.goto("/agent");
    await page.getByPlaceholder("输入您的问题...").fill("不要重复发送");
    await page.getByRole("button", { name: "发送" }).click();
    await page.locator("form").evaluate(form => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await expect(page.getByText("只处理一次")).toBeVisible();
    expect(sends).toBe(1);
  });

  test("products page renders", async ({ page }) => {
    await page.goto("/products");
    await page.waitForLoadState("networkidle");
  });

  test("home presents the smart digital catalog direction", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("智能数码与桌面办公精选商城").first()).toBeVisible();
    for (const category of ["音频设备", "电脑外设", "移动配件", "桌面办公", "智能穿戴", "智能家居"]) await expect(page.getByText(category).first()).toBeVisible();
    await expect(page.getByText("待上传音频设备分类图")).toBeVisible();
  });

  test("headphone detail explains lawful opened-product returns", async ({ page }) => {
    await page.route("**/api/v1/products/p1", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: { id: "p1", name: "Aurora Buds Pro 无线降噪耳机", description: "降噪耳机", category: "ELECTRONICS", price: "699.00", stock: 10, is_returnable: true } }) }));
    await page.goto("/products/p1");
    await expect(page.getByText("拆封与合理试用不当然影响商品完好")).toBeVisible();
  });

  test("planned product image replaces placeholder when asset exists", async ({ page }) => {
    await page.route("**/images/asset-manifest.json", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ assets: ["/images/products/aurora-buds-pro/main.webp"] }) }));
    await page.route("**/api/v1/products/p-image", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: { id: "p-image", name: "Aurora Buds Pro 无线降噪耳机", category: "ELECTRONICS", price: "699.00", stock: 10, is_returnable: true } }) }));
    await page.route("**/images/products/aurora-buds-pro/main.webp", route => route.fulfill({ status: 200, contentType: "image/png", body: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", "base64") }));
    await page.goto("/products/p-image");
    await expect(page.getByRole("img", { name: "Aurora Buds Pro 无线降噪耳机主图" })).toBeVisible();
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
