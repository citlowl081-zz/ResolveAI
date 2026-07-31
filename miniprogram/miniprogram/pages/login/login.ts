import { api, saveTokens } from "../../services/api";

Page({
  data: { email: "", password: "", focusedField: "", loading: false, error: "" },
  onEmail(e: any) { this.setData({ email: e.detail.value }); },
  onPwd(e: any) { this.setData({ password: e.detail.value }); },
  onFocus(e: any) { this.setData({ focusedField: e.currentTarget.dataset.field || "" }); },
  onBlur() { this.setData({ focusedField: "" }); },
  async login() {
    this.setData({ loading: true, error: "" });
    try {
      const res = await api.auth.login(this.data.email, this.data.password);
      if (res.data.success && res.data.data) {
        saveTokens(res.data.data.access_token, res.data.data.refresh_token);
        getApp().globalData.userInfo = res.data.data.user;
        wx.reLaunch({ url: "/pages/index/index" });
      } else {
        this.setData({ error: res.data.message || "登录失败" });
      }
    } catch (e: any) {
      this.setData({ error: e.message || "登录失败" });
    } finally {
      this.setData({ loading: false });
    }
  },
});
