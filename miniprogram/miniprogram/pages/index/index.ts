const app = getApp<IAppOption>();

Page({
  data: { userName: "" },
  onShow() {
    if (!app.globalData.accessToken) { wx.redirectTo({ url: "/pages/login/login" }); return; }
    this.setData({ userName: app.globalData.userInfo?.full_name || "用户" });
  },
});
