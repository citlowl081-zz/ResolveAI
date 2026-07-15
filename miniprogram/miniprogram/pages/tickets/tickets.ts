import { api } from "../../services/api";
import { STATUS_MAP } from "../../utils/util";

Page({
  data: { items: [] as Ticket[], loading: true, statusText: STATUS_MAP },
  async onShow() {
    this.setData({ loading: true });
    try {
      const res = await api.tickets.list();
      if (res.data.success && res.data.data) this.setData({ items: res.data.data.items });
    } catch (e) {} finally { this.setData({ loading: false }); }
  },
  async cancel(e: any) {
    const { id, ver } = e.currentTarget.dataset;
    try {
      await api.tickets.cancel(id, ver);
      wx.showToast({ title: "已取消", icon: "success" });
      this.onShow();
    } catch (err: any) { wx.showToast({ title: err.message || "取消失败", icon: "none" }); }
  },
});
