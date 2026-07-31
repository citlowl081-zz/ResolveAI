import { api } from "../../services/api";
import { LABEL_MAP, STATUS_MAP, uuid } from "../../utils/util";

Page({
  data: { items: [] as Ticket[], loading: true, error: "", statusText: STATUS_MAP, labelText: LABEL_MAP },
  async onShow() {
    this.setData({ loading: true });
    try {
      const res = await api.tickets.list();
      if (res.data.success && res.data.data) this.setData({ items: res.data.data.items });
    } catch (error) { this.setData({ error: (error as Error).message }); }
    finally { this.setData({ loading: false }); }
  },
  async cancel(e: any) {
    const { id, ver } = e.currentTarget.dataset;
    try {
      await api.tickets.cancel(id, ver, uuid());
      wx.showToast({ title: "已取消", icon: "success" });
      this.onShow();
    } catch (err: any) { wx.showToast({ title: err.message || "取消失败", icon: "none" }); }
  },
});
