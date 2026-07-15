import { clearTokens } from "../../services/api";

const app = getApp<IAppOption>();

Page({
  data: { user: { full_name: "", email: "", role: "" } as UserInfo },
  onShow() {
    const u = app.globalData.userInfo;
    if (u) this.setData({ user: u });
  },
  logout() {
    clearTokens();
    app.globalData.userInfo = null;
    wx.redirectTo({ url: "/pages/login/login" });
  },
});
