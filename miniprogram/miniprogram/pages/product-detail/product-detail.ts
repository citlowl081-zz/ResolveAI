import { api } from "../../services/api";
import { addProductToCart } from "../../utils/cart";

const AGENT_SUGGESTION_KEY = "resolveai_agent_suggested_question";

Page({
  data: { product: null as Product | null, loading: true, error: "" },
  async onLoad(options: any) {
    if (!options.id) return;
    try {
      const res = await api.products.get(options.id);
      if (res.data.success && res.data.data) this.setData({ product: res.data.data });
    } catch (error) { this.setData({ error: (error as Error).message }); }
    finally { this.setData({ loading: false }); }
  },
  addToCart() {
    if (!this.data.product) return;
    addProductToCart(this.data.product);
    wx.showToast({ title: "已加入购物车", icon: "success" });
  },
  askAgent() {
    if (!this.data.product) return;
    wx.setStorageSync(
      AGENT_SUGGESTION_KEY,
      `我想了解“${this.data.product.name}”的退换货和售后政策。`,
    );
    wx.switchTab({ url: "/pages/agent/agent" });
  },
});
