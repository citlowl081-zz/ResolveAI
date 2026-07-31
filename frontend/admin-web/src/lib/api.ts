// ── Admin API Client ──
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let onAuthError: (() => void) | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  if (typeof window !== "undefined") {
    localStorage.setItem("admin_at", access);
    localStorage.setItem("admin_rt", refresh);
  }
}
export function loadTokens() {
  if (typeof window !== "undefined") {
    accessToken = localStorage.getItem("admin_at");
    refreshToken = localStorage.getItem("admin_rt");
  }
  return Boolean(accessToken && refreshToken);
}
export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("admin_at");
    localStorage.removeItem("admin_rt");
  }
}
export function onUnauthorized(cb: () => void) {
  onAuthError = cb;
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
  } catch {
    /* */
  }
  return false;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
  isRetry = false,
): Promise<T> {
  loadTokens();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extraHeaders,
  };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("网络连接失败，请检查服务状态");
  }
  if (res.status === 401 && !isRetry) {
    const ok = await refreshAccessToken();
    if (ok) return request(method, path, body, extraHeaders, true);
    clearTokens();
    onAuthError?.();
    throw new Error("登录状态已过期，请重新登录");
  }
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const messages: Record<number, string> = {
      401: "登录状态已过期，请重新登录",
      403: "当前账号无权限执行此操作",
      404: "未找到对应数据",
      409: "该操作已处理，请勿重复提交",
      422: "提交内容不完整或格式不正确",
      500: "系统暂时无法处理，请稍后重试",
    };
    throw new Error(messages[res.status] || "系统暂时无法处理，请稍后重试");
  }
  return json as T;
}

// ── Auth ──
export const adminAuth = {
  login: (email: string, password: string) =>
    request<{ success: boolean; data: TokenData & { user: UserInfo } }>(
      "POST",
      "/auth/login",
      { email, password },
    ),
  me: () => request<{ success: boolean; data: UserInfo }>("GET", "/auth/me"),
};

// ── Tickets ──
export const adminTickets = {
  list: (page = 1, status?: string) => {
    const p = new URLSearchParams({ page: String(page), page_size: "20" });
    if (status) p.set("status", status);
    return request<{ success: boolean; data: PaginatedResponse<Ticket> }>(
      "GET",
      `/admin/after-sales/tickets?${p}`,
    );
  },
  get: (id: string) =>
    request<{ success: boolean; data: Ticket }>(
      "GET",
      `/admin/after-sales/tickets/${id}`,
    ),
};

// ── Policies ──
export const adminPolicies = {
  list: (page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<Policy> }>(
      "GET",
      `/admin/policies?page=${page}&page_size=20`,
    ),
  getByKey: (key: string) =>
    request<{ success: boolean; data: Policy }>(
      "GET",
      `/admin/policies/by-key/${key}`,
    ),
  create: (data: Record<string, unknown>) =>
    request<{ success: boolean; data: Policy }>(
      "POST",
      "/admin/policies",
      data,
    ),
  update: (id: string, data: Record<string, unknown>) =>
    request<{ success: boolean; data: Policy }>(
      "PATCH",
      `/admin/policies/${id}`,
      data,
    ),
  versionHistory: (key: string) =>
    request<{ success: boolean; data: { versions: Policy[] } }>(
      "GET",
      `/admin/policies/by-key/${key}/versions`,
    ),
};

// ── Approvals ──
export const adminApprovals = {
  list: (page = 1, status?: string) => {
    const p = new URLSearchParams({ page: String(page), page_size: "20" });
    if (status) p.set("status", status);
    return request<{ success: boolean; data: PaginatedResponse<ApprovalTask> }>(
      "GET",
      `/admin/approvals?${p}`,
    );
  },
  get: (id: string) =>
    request<{ success: boolean; data: ApprovalTask }>(
      "GET",
      `/admin/approvals/${id}`,
    ),
  approve: (id: string, version: number, reason: string, idemKey: string) =>
    request<{ success: boolean; data: ApprovalTask }>(
      "POST",
      `/admin/approvals/${id}/approve`,
      { expected_version: version, decision_reason: reason },
      { "Idempotency-Key": idemKey },
    ),
  reject: (id: string, version: number, reason: string, idemKey: string) =>
    request<{ success: boolean; data: ApprovalTask }>(
      "POST",
      `/admin/approvals/${id}/reject`,
      { expected_version: version, decision_reason: reason },
      { "Idempotency-Key": idemKey },
    ),
  execute: (id: string, idemKey: string) =>
    request<{ success: boolean; data: Record<string, unknown> }>(
      "POST",
      `/admin/approvals/${id}/execute`,
      undefined,
      { "Idempotency-Key": idemKey },
    ),
};

// ── Agent traces ──
export const adminTraces = {
  list: (page = 1, sessionId?: string) => {
    const p = new URLSearchParams({ page: String(page), page_size: "50" });
    if (sessionId) p.set("session_id", sessionId);
    return request<{ success: boolean; data: PaginatedResponse<AgentTrace> }>(
      "GET",
      `/admin/agent/traces?${p}`,
    );
  },
  get: (id: string) =>
    request<{
      success: boolean;
      data: { trace_id: string; nodes: AgentTrace[] };
    }>("GET", `/admin/agent/traces/${id}`),
};

// ── Tool logs ──
export const adminToolLogs = {
  list: (page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<ToolLog> }>(
      "GET",
      `/admin/agent/tool-logs?page=${page}&page_size=50`,
    ),
  get: (id: string) =>
    request<{ success: boolean; data: ToolLog }>(
      "GET",
      `/admin/agent/tool-logs/${id}`,
    ),
};

export const adminConsole = {
  dashboard: (days = 7) =>
    request<{ success: boolean; data: DashboardMetrics }>(
      "GET",
      `/admin/console/dashboard?days=${days}`,
    ),
  orders: (page = 1, query = "", status = "") => {
    const p = new URLSearchParams({ page: String(page), page_size: "20" });
    if (query) p.set("query", query);
    if (status) p.set("status", status);
    return request<{ success: boolean; data: PaginatedResponse<AdminOrder> }>(
      "GET",
      `/admin/console/orders?${p}`,
    );
  },
  order: (id: string) =>
    request<{ success: boolean; data: AdminOrderDetail }>(
      "GET",
      `/admin/console/orders/${id}`,
    ),
  users: (page = 1, query = "", role = "") => {
    const p = new URLSearchParams({ page: String(page), page_size: "20" });
    if (query) p.set("query", query);
    if (role) p.set("role", role);
    return request<{ success: boolean; data: PaginatedResponse<AdminUser> }>(
      "GET",
      `/admin/console/users?${p}`,
    );
  },
  user: (id: string) =>
    request<{ success: boolean; data: AdminUserDetail }>(
      "GET",
      `/admin/console/users/${id}`,
    ),
  system: () =>
    request<{ success: boolean; data: SystemStatus }>(
      "GET",
      "/admin/console/system-status",
    ),
};

export const adminProducts = {
  list: (page = 1) =>
    request<{ success: boolean; data: PaginatedResponse<Product> }>(
      "GET",
      `/products?page=${page}&page_size=100`,
    ),
  listAll: async () => {
    const all: Product[] = [];
    let page = 1;
    let totalPages = 1;
    do {
      const response = await adminProducts.list(page);
      if (response.data) {
        all.push(...response.data.items);
        totalPages = response.data.total_pages;
      }
      page += 1;
    } while (page <= totalPages);
    return all;
  },
  get: (id: string) =>
    request<{ success: boolean; data: Product }>("GET", `/products/${id}`),
};

// ── Types ──
import type {
  UserInfo,
  TokenData,
  Ticket,
  Policy,
  ApprovalTask,
  AgentTrace,
  ToolLog,
  PaginatedResponse,
  Product,
  DashboardMetrics,
  AdminOrder,
  AdminOrderDetail,
  AdminUser,
  AdminUserDetail,
  SystemStatus,
} from "./types";
export type {
  UserInfo,
  TokenData,
  Ticket,
  Policy,
  ApprovalTask,
  AgentTrace,
  ToolLog,
  PaginatedResponse,
  Product,
  DashboardMetrics,
  AdminOrder,
  AdminOrderDetail,
  AdminUser,
  AdminUserDetail,
  SystemStatus,
};
