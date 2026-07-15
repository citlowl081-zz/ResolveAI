"use strict";
App({
  globalData: { accessToken: "", refreshToken: "", userInfo: null, apiBase: "http://localhost:8000/api/v1" },
  onLaunch() {
    const token = wx.getStorageSync("access_token");
    const refresh = wx.getStorageSync("refresh_token");
    if (token) { this.globalData.accessToken = token; this.globalData.refreshToken = refresh || ""; }
  },
});
