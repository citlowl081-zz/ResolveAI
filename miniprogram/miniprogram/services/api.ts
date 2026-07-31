const app = getApp<IAppOption>();

type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

interface RequestOptions {
  auth?: boolean;
  idempotencyKey?: string;
  retryAuth?: boolean;
  timeout?: number;
}

const ERROR_BY_STATUS: Record<number, string> = {
  401: "登录状态已过期，请重新登录",
  403: "当前账号无权限执行此操作",
  404: "未找到对应数据",
  409: "该操作已处理，请勿重复提交",
  422: "提交内容不完整或格式不正确",
  500: "系统暂时无法处理，请稍后重试",
};

const ERROR_BY_CODE: Record<string, string> = {
  ACTION_ALREADY_CONSUMED: ERROR_BY_STATUS[409],
  CONFLICT: ERROR_BY_STATUS[409],
  FORBIDDEN: ERROR_BY_STATUS[403],
  NOT_FOUND: ERROR_BY_STATUS[404],
  VALIDATION_ERROR: ERROR_BY_STATUS[422],
};

function getBase(): string { return app.globalData.apiBase; }
function getToken(): string { return app.globalData.accessToken; }

function saveTokens(access: string, refresh: string) {
  app.globalData.accessToken = access;
  app.globalData.refreshToken = refresh;
  wx.setStorageSync("access_token", access);
  wx.setStorageSync("refresh_token", refresh);
}

function clearTokens() {
  app.globalData.accessToken = "";
  app.globalData.refreshToken = "";
  wx.removeStorageSync("access_token");
  wx.removeStorageSync("refresh_token");
}

function friendlyError(statusCode: number, data?: APIResponse<unknown>): string {
  if (statusCode >= 500) return ERROR_BY_STATUS[500];
  if (ERROR_BY_STATUS[statusCode]) return ERROR_BY_STATUS[statusCode];
  if (data?.code && ERROR_BY_CODE[data.code]) return ERROR_BY_CODE[data.code];
  return "操作未完成，请稍后重试";
}

async function refreshToken(): Promise<boolean> {
  const refresh = app.globalData.refreshToken;
  if (!refresh) return false;
  try {
    const response = await request<APIResponse<{ access_token: string; refresh_token: string }>>(
      "POST", "/auth/refresh", { refresh_token: refresh },
      { auth: false, retryAuth: false },
    );
    if (response.data.success && response.data.data) {
      saveTokens(response.data.data.access_token, response.data.data.refresh_token);
      return true;
    }
  } catch {
    // Authentication failure is handled by the original request.
  }
  return false;
}

function request<T>(
  method: HttpMethod,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<WechatMiniprogram.RequestSuccessCallbackResult & { data: T }> {
  const { auth = true, idempotencyKey, retryAuth = true, timeout = 60000 } = options;
  return new Promise((resolve, reject) => {
    const header: Record<string, string> = { "Content-Type": "application/json" };
    if (auth && getToken()) header.Authorization = `Bearer ${getToken()}`;
    if (idempotencyKey) header["Idempotency-Key"] = idempotencyKey;

    wx.request({
      url: `${getBase()}${path}`,
      method,
      header,
      data: body,
      timeout,
      success(result) {
        const response = result as WechatMiniprogram.RequestSuccessCallbackResult & { data: T };
        const envelope = result.data as APIResponse<unknown> | undefined;
        if (result.statusCode === 401 && auth && retryAuth) {
          void refreshToken().then((refreshed) => {
            if (refreshed) {
              request<T>(method, path, body, { ...options, retryAuth: false }).then(resolve, reject);
              return;
            }
            clearTokens();
            wx.reLaunch({ url: "/pages/login/login" });
            reject(new Error(ERROR_BY_STATUS[401]));
          });
          return;
        }
        if (result.statusCode >= 200 && result.statusCode < 300) {
          if (envelope && envelope.success === false) {
            reject(new Error(friendlyError(result.statusCode, envelope)));
          } else {
            resolve(response);
          }
          return;
        }
        reject(new Error(friendlyError(result.statusCode, envelope)));
      },
      fail() {
        reject(new Error("网络连接失败，请检查后端服务"));
      },
    });
  });
}

export const api = {
  auth: {
    login: (email: string, password: string) => request<APIResponse<{ access_token: string; refresh_token: string; user: UserInfo }>>("POST", "/auth/login", { email, password }, { auth: false }),
    register: (email: string, password: string, fullName: string) => request<APIResponse<null>>("POST", "/auth/register", { email, password, full_name: fullName }, { auth: false }),
    me: () => request<APIResponse<UserInfo>>("GET", "/auth/me"),
  },
  products: {
    list: (page = 1) => request<APIResponse<PaginatedResponse<Product>>>("GET", `/products?page=${page}&page_size=50`),
    get: (id: string) => request<APIResponse<Product>>("GET", `/products/${id}`),
  },
  orders: {
    list: (page = 1) => request<APIResponse<PaginatedResponse<Order>>>("GET", `/orders?page=${page}&page_size=20`),
    get: (id: string) => request<APIResponse<Order>>("GET", `/orders/${id}`),
  },
  logistics: {
    get: (orderId: string) => request<APIResponse<LogisticsInfo>>("GET", `/orders/${orderId}/logistics`),
  },
  tickets: {
    list: (page = 1) => request<APIResponse<PaginatedResponse<Ticket>>>("GET", `/after-sales/tickets?page=${page}&page_size=20`),
    get: (id: string) => request<APIResponse<Ticket>>("GET", `/after-sales/tickets/${id}`),
    cancel: (id: string, version: number, idempotencyKey: string) => request<APIResponse<Ticket>>(
      "POST", `/after-sales/tickets/${id}/cancel`, { expected_version: version }, { idempotencyKey },
    ),
  },
  agent: {
    createSession: (message: string, clientMessageId: string) => request<APIResponse<AgentTurnResponse>>(
      "POST", "/agent/sessions", { message, client_message_id: clientMessageId },
      { idempotencyKey: clientMessageId, timeout: 120000 },
    ),
    sendMessage: (sessionId: string, message: string, confirmActionId: string | null, clientMessageId: string) => {
      const body: Record<string, unknown> = { message, client_message_id: clientMessageId };
      if (confirmActionId) body.confirm_action_id = confirmActionId;
      return request<APIResponse<AgentTurnResponse>>(
        "POST", `/agent/sessions/${sessionId}/messages`, body,
        { idempotencyKey: clientMessageId, timeout: 120000 },
      );
    },
    listSessions: (page = 1) => request<APIResponse<PaginatedResponse<AgentSession>>>("GET", `/agent/sessions?page=${page}&page_size=20`),
    getMessages: (sessionId: string, page = 1) => request<APIResponse<PaginatedResponse<AgentMessage>>>("GET", `/agent/sessions/${sessionId}/messages?page=${page}&page_size=100`),
  },
  memories: {
    list: (page = 1) => request<APIResponse<PaginatedResponse<Memory>>>("GET", `/memories?page=${page}&page_size=50`),
    create: (data: MemoryCreateInput) => request<APIResponse<Memory>>("POST", "/memories", data),
    update: (id: string, data: MemoryUpdateInput) => request<APIResponse<Memory>>("PATCH", `/memories/${id}`, data),
    delete: (id: string) => request<APIResponse<null>>("DELETE", `/memories/${id}`),
  },
  approvals: {
    list: (page = 1) => request<APIResponse<PaginatedResponse<Approval>>>("GET", `/approvals?page=${page}&page_size=20`),
    get: (id: string) => request<APIResponse<Approval>>("GET", `/approvals/${id}`),
  },
};

export { clearTokens, getToken, request, saveTokens };
