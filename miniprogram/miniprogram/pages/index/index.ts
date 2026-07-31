import { api } from "../../services/api";
import { CATALOG_CATEGORIES, enrichProduct } from "../../utils/catalog";

const app = getApp<IAppOption>();

Page({
  data: {
    userName: "",
    search: "",
    categories: CATALOG_CATEGORIES,
    recommended: [] as CatalogProduct[],
    popular: [] as CatalogProduct[],
    newItems: [] as CatalogProduct[],
    loading: true,
    error: "",
  },

  async onShow() {
    if (!app.globalData.accessToken) { wx.redirectTo({ url: "/pages/login/login" }); return; }
    try {
      if (!app.globalData.userInfo) {
        const userResponse = await api.auth.me();
        if (userResponse.data.data) app.globalData.userInfo = userResponse.data.data;
      }
      const response = await api.products.list();
      const items = (response.data.data?.items || []).map(enrichProduct);
      this.setData({
        userName: app.globalData.userInfo?.full_name || "用户",
        recommended: items.slice(0, 4),
        popular: items.slice(4, 8),
        newItems: items.slice(8, 12),
        loading: false,
        error: "",
      });
    } catch (error) {
      this.setData({ loading: false, error: (error as Error).message });
    }
  },

  onSearchInput(event: WechatMiniprogram.Input) {
    this.setData({ search: event.detail.value });
  },

  searchProducts() {
    const query = this.data.search.trim();
    const url = query
      ? `/pages/products/products?q=${encodeURIComponent(query)}`
      : "/pages/products/products";
    wx.navigateTo({ url });
  },
});
