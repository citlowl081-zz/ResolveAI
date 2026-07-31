import { api } from "../../services/api";
import { LABEL_MAP } from "../../utils/util";

Page({
  data: {
    items: [] as Memory[], loading: true, error: "", showForm: false,
    typeIdx: 0, typeOptions: ["PREFERENCE", "FACT", "SUMMARY", "COMMITMENT", "RISK_PROFILE"],
    typeLabels: ["偏好", "事实", "摘要", "承诺", "风险偏好"],
    memKey: "", memContent: "", editingId: "", editingContent: "", labelText: LABEL_MAP,
  },
  onShow() { void this.load(); },
  async load() {
    this.setData({ loading: true, error: "" });
    try {
      const response = await api.memories.list();
      this.setData({ items: response.data.data?.items || [] });
    } catch (error) { this.setData({ error: (error as Error).message }); }
    finally { this.setData({ loading: false }); }
  },
  toggleForm() { this.setData({ showForm: !this.data.showForm }); },
  onType(event: any) { this.setData({ typeIdx: Number(event.detail.value) }); },
  onKey(event: any) { this.setData({ memKey: event.detail.value }); },
  onContent(event: any) { this.setData({ memContent: event.detail.value }); },
  onEditingContent(event: any) { this.setData({ editingContent: event.detail.value }); },
  async create() {
    const content = this.data.memContent.trim();
    if (!content) return;
    try {
      const memoryType = this.data.typeOptions[this.data.typeIdx];
      await api.memories.create({ memory_type: memoryType, content, key: this.data.memKey.trim() || undefined, source: "explicit_api", confidence: 1 });
      wx.showToast({ title: "记忆已保存", icon: "success" });
      this.setData({ showForm: false, memContent: "", memKey: "" });
      await this.load();
    } catch (error) { wx.showToast({ title: (error as Error).message, icon: "none" }); }
  },
  edit(event: any) {
    const id = event.currentTarget.dataset.id as string;
    const item = this.data.items.find((memory) => memory.id === id);
    if (item) this.setData({ editingId: id, editingContent: item.content });
  },
  cancelEdit() { this.setData({ editingId: "", editingContent: "" }); },
  async update() {
    const content = this.data.editingContent.trim();
    if (!this.data.editingId || !content) return;
    try {
      await api.memories.update(this.data.editingId, { content });
      wx.showToast({ title: "记忆已更新", icon: "success" });
      this.cancelEdit();
      await this.load();
    } catch (error) { wx.showToast({ title: (error as Error).message, icon: "none" }); }
  },
  remove(event: any) {
    const id = event.currentTarget.dataset.id as string;
    wx.showModal({
      title: "删除长期记忆", content: "删除后，新会话将不再使用这条记忆。", confirmText: "确认删除",
      success: (result) => { if (result.confirm) void this.deleteMemory(id); },
    });
  },
  async deleteMemory(id: string) {
    try {
      await api.memories.delete(id);
      wx.showToast({ title: "记忆已删除", icon: "success" });
      await this.load();
    } catch (error) { wx.showToast({ title: (error as Error).message, icon: "none" }); }
  },
});
