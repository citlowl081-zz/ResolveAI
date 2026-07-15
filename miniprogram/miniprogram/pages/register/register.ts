import { api } from "../../services/api";

Page({
  data: { name: "", email: "", password: "", loading: false, error: "" },
  onName(e: any) { this.setData({ name: e.detail.value }); },
  onEmail(e: any) { this.setData({ email: e.detail.value }); },
  onPwd(e: any) { this.setData({ password: e.detail.value }); },
  async register() {
    this.setData({ loading: true, error: "" });
    try {
      const res = await api.auth.register(this.data.email, this.data.password, this.data.name);
      if (res.data.success) {
        wx.showToast({ title: "注册成功", icon: "success" });
        setTimeout(() => wx.navigateBack(), 1500);
      } else {
        this.setData({ error: "注册失败" });
      }
    } catch (e: any) { this.setData({ error: e.message || "注册失败" }); }
    finally { this.setData({ loading: false }); }
  },
});
