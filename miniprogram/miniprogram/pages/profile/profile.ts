import { api, clearTokens } from "../../services/api";

const app = getApp<IAppOption>();

Page({
  data: { user: { full_name: "", email: "", role: "" } as UserInfo, userInitial: "我", roleText: { CUSTOMER: "顾客", ADMIN: "管理员" } as Record<string, string> },
  async onShow() {
    let user = app.globalData.userInfo;
    if (!user && app.globalData.accessToken) {
      try {
        const response = await api.auth.me();
        user = response.data.data;
        app.globalData.userInfo = user;
      } catch { return; }
    }
    if (user) this.setData({ user, userInitial: user.full_name.slice(0, 1) || "我" });
  },
  logout() {
    clearTokens();
    app.globalData.userInfo = null;
    wx.redirectTo({ url: "/pages/login/login" });
  },
});
