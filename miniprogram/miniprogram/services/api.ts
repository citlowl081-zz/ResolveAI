const app = getApp<IAppOption>();

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

async function refreshToken(): Promise<boolean> {
  const rt = app.globalData.refreshToken;
  if (!rt) return false;
  try {
    const res = await wxRequest<APIResponse<{access_token:string;refresh_token:string}>>("POST", "/auth/refresh", { refresh_token: rt }, false);
    if (res.data && res.data.success && res.data.data) {
      saveTokens(res.data.data.access_token, res.data.data.refresh_token);
      return true;
    }
  } catch (e) { /* ignore */ }
  return false;
}

function wxRequest<T>(method: string, path: string, body?: any, auth = true, isRetry = false): Promise<WechatMiniprogram.RequestSuccessCallbackResult & { data: T }> {
  return new Promise((resolve, reject) => {
    const header: Record<string, string> = { "Content-Type": "application/json" };
    if (auth && getToken()) header["Authorization"] = `Bearer ${getToken()}`;
    wx.request({
      url: `${getBase()}${path}`,
      method: method as any,
      header,
      data: body,
      success(res: any) {
        if (res.statusCode === 401 && auth && !isRetry) {
          refreshToken().then(ok => {
            if (ok) resolve(wxRequest<T>(method, path, body, auth, true));
            else { clearTokens(); wx.redirectTo({ url: "/pages/login/login" }); reject(new Error("认证过期")); }
          });
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res);
        else reject(new Error((res.data as any)?.message || `请求失败: ${res.statusCode}`));
      },
      fail(err: any) { reject(new Error(err.errMsg || "网络错误")); }
    });
  });
}

// API wrappers
export const api = {
  auth: {
    login: (email: string, password: string) => wxRequest<APIResponse<{access_token:string;refresh_token:string;user:UserInfo}>>("POST", "/auth/login", { email, password }, false),
    register: (email: string, password: string, full_name: string) => wxRequest<APIResponse<null>>("POST", "/auth/register", { email, password, full_name }, false),
    me: () => wxRequest<APIResponse<UserInfo>>("GET", "/auth/me"),
  },
  products: {
    list: (page=1) => wxRequest<APIResponse<PaginatedResponse<Product>>>("GET", `/products?page=${page}&page_size=20`),
    get: (id:string) => wxRequest<APIResponse<Product>>("GET", `/products/${id}`),
  },
  orders: {
    list: (page=1) => wxRequest<APIResponse<PaginatedResponse<Order>>>("GET", `/orders?page=${page}&page_size=20`),
    get: (id:string) => wxRequest<APIResponse<Order>>("GET", `/orders/${id}`),
  },
  logistics: {
    get: (orderId:string) => wxRequest<APIResponse<LogisticsInfo>>("GET", `/logistics/${orderId}`),
  },
  tickets: {
    list: (page=1) => wxRequest<APIResponse<PaginatedResponse<Ticket>>>("GET", `/after-sales/tickets?page=${page}&page_size=20`),
    get: (id:string) => wxRequest<APIResponse<Ticket>>("GET", `/after-sales/tickets/${id}`),
    cancel: (id:string, version:number) => wxRequest<APIResponse<Ticket>>("POST", `/after-sales/tickets/${id}/cancel`, { expected_version: version }),
  },
  agent: {
    createSession: (message:string, idemKey:string) => {
      const header: Record<string,string> = { "Content-Type":"application/json", "Idempotency-Key": idemKey };
      if (getToken()) header["Authorization"] = `Bearer ${getToken()}`;
      return new Promise<any>((resolve, reject) => {
        wx.request({ url: `${getBase()}/agent/sessions`, method: "POST", header, data: { message }, success: r => resolve(r.data), fail: e => reject(e) });
      });
    },
    sendMessage: (sessionId:string, message:string, confirmActionId:string|null, idemKey:string) => {
      const header: Record<string,string> = { "Content-Type":"application/json", "Idempotency-Key": idemKey };
      if (getToken()) header["Authorization"] = `Bearer ${getToken()}`;
      const body: any = { message };
      if (confirmActionId) body.confirm_action_id = confirmActionId;
      return new Promise<any>((resolve, reject) => {
        wx.request({ url: `${getBase()}/agent/sessions/${sessionId}/messages`, method: "POST", header, data: body, success: r => resolve(r.data), fail: e => reject(e) });
      });
    },
  },
  memories: {
    list: (page=1) => wxRequest<APIResponse<PaginatedResponse<Memory>>>("GET", `/memories?page=${page}&page_size=50`),
    create: (data:any) => wxRequest<APIResponse<Memory>>("POST", "/memories", data),
    update: (id:string, data:any) => wxRequest<APIResponse<Memory>>("PATCH", `/memories/${id}`, data),
    delete: (id:string) => wxRequest<APIResponse<null>>("DELETE", `/memories/${id}`),
  },
  approvals: {
    list: (page=1) => wxRequest<APIResponse<PaginatedResponse<Approval>>>("GET", `/approvals?page=${page}&page_size=20`),
  },
};

export { saveTokens, clearTokens, getToken };
