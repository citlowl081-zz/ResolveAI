import { api } from "../../services/api";

Page({
  data: { items: [] as Memory[], loading: true, showForm: false, typeIdx: 0, typeOptions: ["PREFERENCE","FACT","SUMMARY","COMMITMENT","RISK_PROFILE"], memKey: "", memContent: "" },
  onShow() { this.load(); },
  async load() {
    this.setData({ loading: true });
    try { const r = await api.memories.list(); if (r.data.success && r.data.data) this.setData({ items: r.data.data.items }); } catch (e) {} finally { this.setData({ loading: false }); }
  },
  toggleForm() { this.setData({ showForm: !this.data.showForm }); },
  onType(e: any) { this.setData({ typeIdx: parseInt(e.detail.value) }); },
  onKey(e: any) { this.setData({ memKey: e.detail.value }); },
  onContent(e: any) { this.setData({ memContent: e.detail.value }); },
  async create() {
    if (!this.data.memContent.trim()) return;
    try {
      const t = this.data.typeOptions[this.data.typeIdx];
      await api.memories.create({ memory_type: t, content: this.data.memContent, key: this.data.memKey || undefined });
      this.setData({ showForm: false, memContent: "", memKey: "" });
      this.load();
    } catch (e: any) { wx.showToast({ title: e.message, icon: "none" }); }
  },
  async remove(e: any) {
    try { await api.memories.delete(e.currentTarget.dataset.id); this.load(); } catch (err: any) { wx.showToast({ title: err.message, icon: "none" }); }
  },
});
