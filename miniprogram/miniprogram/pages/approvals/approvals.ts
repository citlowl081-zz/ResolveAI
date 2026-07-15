import { api } from "../../services/api";

Page({
  data: { items: [] as Approval[], loading: true },
  async onShow() {
    this.setData({ loading: true });
    try { const r = await api.approvals.list(); if (r.data.success && r.data.data) this.setData({ items: r.data.data.items }); } catch (e) {} finally { this.setData({ loading: false }); }
  },
});
