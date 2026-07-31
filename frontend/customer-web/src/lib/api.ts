// ── API Client ──
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let onAuthError: (() => void) | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  }
}

export function loadTokens() {
  if (typeof window !== "undefined") {
    accessToken = localStorage.getItem("access_token");
    refreshToken = localStorage.getItem("refresh_token");
  }
  return Boolean(accessToken && refreshToken);
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }
}

export function getAccessToken() { return accessToken; }
export function onUnauthorized(cb: () => void) { onAuthError = cb; }

function idempotencyKey(): string {
  return crypto.randomUUID();
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const json = await res.json();
    if (json.success && json.data) {
      setTokens(json.data.access_token, json.data.refresh_token);
      return true;
    }
  } catch { /* network error */ }
  return false;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  isRetry = false,
  extraHeaders: Record<string, string> = {},
): Promise<T> {
  loadTokens();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extraHeaders,
  };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  let res: Response;
  try { res = await fetch(`${API_BASE}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined }); }
  catch { throw new ApiError(0, "网络连接失败，请检查服务状态"); }

  if (res.status === 401 && !isRetry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request<T>(method, path, body, true, extraHeaders);
    clearTokens();
    onAuthError?.();
    throw new ApiError(401, "登录状态已过期，请重新登录");
  }

  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code = typeof json.code === "string" ? json.code : "";
    const raw = typeof json.message === "string" ? json.message : "";
    const messages: Record<number, string> = { 401: "登录状态已过期，请重新登录", 403: "当前账号无权限执行此操作", 404: "未找到对应数据", 409: "该操作已处理，请勿重复提交", 422: "提交内容不完整或格式不正确", 500: "系统暂时无法处理，请稍后重试" };
    const message = code === "ACTION_ALREADY_CONSUMED" ? messages[409] : messages[res.status] || (raw && !/Request failed|Error \d+|CONFLICT|Internal Server Error/i.test(raw) ? raw : "系统暂时无法处理，请稍后重试");
    throw new ApiError(res.status, message);
  }
  return json as T;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

// ── Auth ──
export const auth = {
  register: (email: string, password: string, full_name: string) =>
    request<{ success: boolean; data: UserInfo }>("POST", "/auth/register", { email, password, full_name }),
  login: (email: string, password: string) =>
    request<{ success: boolean; data: TokenData & { user: UserInfo } }>("POST", "/auth/login", { email, password }),
  me: () => request<{ success: boolean; data: UserInfo }>("GET", "/auth/me"),
};

// ── Products ──
export const products = {
  list: (page = 1, category?: string, pageSize = 20) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (category) params.set("category", category);
    return request<{ success: boolean; data: PaginatedResponse<Product> }>("GET", `/products?${params}`);
  },
  listAll: async () => {
    const all: Product[] = [];
    let page = 1;
    let totalPages = 1;
    do {
      const response = await products.list(page, undefined, 100);
      if (response.data) { all.push(...response.data.items); totalPages = response.data.total_pages; }
      page += 1;
    } while (page <= totalPages);
    return all;
  },
  get: (id: string) => request<{ success: boolean; data: Product }>("GET", `/products/${id}`),
};

// ── Orders ──
export const orders = {
  list: (page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<Order> }>("GET", `/orders?page=${page}&page_size=20`),
  get: (id: string) => request<{ success: boolean; data: Order }>("GET", `/orders/${id}`),
};

// ── Logistics ──
export const logistics = {
  get: (orderId: string) =>
    request<{ success: boolean; data: LogisticsInfo }>("GET", `/orders/${orderId}/logistics`),
};

// ── After-Sales ──
export const afterSales = {
  create: (orderId: string, intent: string, requestedItems: unknown[], customerRequest: string) =>
    request<{ success: boolean; data: Ticket }>("POST", "/after-sales/tickets", {
      order_id: orderId, intent, requested_items: requestedItems, customer_request: customerRequest,
    }, false, { "Idempotency-Key": idempotencyKey() }),
  list: (page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<Ticket> }>("GET", `/after-sales/tickets?page=${page}&page_size=20`),
  get: (id: string) => request<{ success: boolean; data: Ticket }>("GET", `/after-sales/tickets/${id}`),
  cancel: (id: string, version: number) =>
    request<{ success: boolean; data: Ticket }>(
      "POST", `/after-sales/tickets/${id}/cancel`, { expected_version: version },
      false, { "Idempotency-Key": idempotencyKey() },
    ),
};

// ── Agent ──
export const agent = {
  createSession: (message: string, clientMessageId: string) =>
    request<{ success: boolean; data: AgentResponse }>(
      "POST", "/agent/sessions", { message, client_message_id: clientMessageId }, false,
      { "Idempotency-Key": clientMessageId },
    ),
  sendMessage: (sessionId: string, message: string, confirmActionId: string | null, clientMessageId: string) => {
    const body: Record<string, unknown> = { message, client_message_id: clientMessageId };
    if (confirmActionId) body["confirm_action_id"] = confirmActionId;
    return request<{ success: boolean; data: AgentResponse }>(
      "POST", `/agent/sessions/${sessionId}/messages`, body, false,
      { "Idempotency-Key": clientMessageId },
    );
  },
  listSessions: (page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<AgentSession> }>("GET", `/agent/sessions?page=${page}&page_size=20`),
  getMessages: (sessionId: string, page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<AgentMessage> }>("GET", `/agent/sessions/${sessionId}/messages?page=${page}&page_size=100`),
  closeSession: (sessionId: string, idempotencyKey: string) =>
    request<{ success: boolean; data: AgentSession }>(
      "POST", `/agent/sessions/${sessionId}/close`, undefined, false,
      { "Idempotency-Key": idempotencyKey },
    ),
};

// ── Memories ──
export const memories = {
  list: (page = 1, type?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: "50" });
    if (type) params.set("memory_type", type);
    return request<{ success: boolean; data: PaginatedResponse<UserMemory> }>("GET", `/memories?${params}`);
  },
  create: (data: { memory_type: string; content: string; key?: string; source?: string; structured_data?: Record<string, unknown> }) =>
    request<{ success: boolean; data: UserMemory }>("POST", "/memories", data),
  update: (id: string, data: { content?: string; status?: string }) =>
    request<{ success: boolean; data: UserMemory }>("PATCH", `/memories/${id}`, data),
  delete: (id: string) => request<{ success: boolean }>("DELETE", `/memories/${id}`),
};

// ── Approvals ──
export const approvals = {
  list: (page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<ApprovalTask> }>("GET", `/approvals?page=${page}&page_size=20`),
  get: (id: string) => request<{ success: boolean; data: ApprovalTask }>("GET", `/approvals/${id}`),
};

// ── Types ──
import type {
  APIResponse, UserInfo, TokenData, Product, Order, OrderItem,
  LogisticsInfo, LogisticsEvent, Ticket, ProposedAction, Citation,
  AgentMessage, AgentSession, AgentResponse, UserMemory,
  ApprovalTask, PaginatedResponse, Policy, AgentTrace, ToolLog, DashboardData,
} from "./types";
export type {
  APIResponse, UserInfo, TokenData, Product, Order, OrderItem,
  LogisticsInfo, LogisticsEvent, Ticket, ProposedAction, Citation,
  AgentMessage, AgentSession, AgentResponse, UserMemory,
  ApprovalTask, PaginatedResponse, Policy, AgentTrace, ToolLog, DashboardData,
};
