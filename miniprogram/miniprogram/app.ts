App<IAppOption>({
  globalData: {
    accessToken: "",
    refreshToken: "",
    userInfo: null,
    apiBase: "http://localhost:8000/api/v1",
  },
  onLaunch() {
    const token = wx.getStorageSync("access_token");
    const refresh = wx.getStorageSync("refresh_token");
    if (token) {
      this.globalData.accessToken = token;
      this.globalData.refreshToken = refresh || "";
    }
  },
});

interface IAppOption {
  globalData: {
    accessToken: string;
    refreshToken: string;
    userInfo: UserInfo | null;
    apiBase: string;
  };
}

interface UserInfo {
  id: string;
  email: string;
  full_name: string;
  role: string;
}
