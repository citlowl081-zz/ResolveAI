import { loadCart, saveCart } from "../../utils/cart";
import { api } from "../../services/api";

const app = getApp<IAppOption>();

Page({
  data: {
    items: [] as CartItem[],
    allSelected: false,
    selectedCount: 0,
    total: "0.00",
  },

  async onShow() {
    if (!app.globalData.accessToken) { wx.reLaunch({ url: "/pages/login/login" }); return; }
    if (!app.globalData.userInfo) {
      try {
        const response = await api.auth.me();
        if (response.data.data) app.globalData.userInfo = response.data.data;
      } catch { return; }
    }
    this.refresh(loadCart());
  },

  refresh(items: CartItem[]) {
    const selected = items.filter((item) => item.selected);
    const total = selected.reduce(
      (sum, item) => sum + Number(item.product.price) * item.quantity, 0,
    );
    saveCart(items);
    this.setData({
      items,
      allSelected: items.length > 0 && selected.length === items.length,
      selectedCount: selected.reduce((sum, item) => sum + item.quantity, 0),
      total: total.toFixed(2),
    });
  },

  toggleItem(event: WechatMiniprogram.TouchEvent) {
    const id = event.currentTarget.dataset.id as string;
    this.refresh(this.data.items.map((item) =>
      item.product.id === id ? { ...item, selected: !item.selected } : item,
    ));
  },

  toggleAll() {
    const selected = !this.data.allSelected;
    this.refresh(this.data.items.map((item) => ({ ...item, selected })));
  },

  changeQuantity(event: WechatMiniprogram.TouchEvent) {
    const id = event.currentTarget.dataset.id as string;
    const delta = Number(event.currentTarget.dataset.delta);
    this.refresh(this.data.items.map((item) => item.product.id === id
      ? { ...item, quantity: Math.max(1, item.quantity + delta) }
      : item));
  },

  removeItem(event: WechatMiniprogram.TouchEvent) {
    const id = event.currentTarget.dataset.id as string;
    this.refresh(this.data.items.filter((item) => item.product.id !== id));
  },

  showCheckoutBoundary() {
    wx.showModal({
      title: "演示说明",
      content: "当前演示版本暂未开放在线结算",
      showCancel: false,
    });
  },
});
