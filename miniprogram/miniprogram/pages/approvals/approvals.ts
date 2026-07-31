import { api } from "../../services/api";
import { LABEL_MAP, STATUS_MAP } from "../../utils/util";

Page({
  data: {
    items: [] as Approval[], selected: null as Approval | null,
    loading: true, detailLoading: false, error: "",
    statusText: STATUS_MAP, labelText: LABEL_MAP,
  },
  async onShow() {
    this.setData({ loading: true, error: "" });
    try {
      const response = await api.approvals.list();
      this.setData({ items: response.data.data?.items || [] });
    } catch (error) { this.setData({ error: (error as Error).message }); }
    finally { this.setData({ loading: false }); }
  },
  async showDetail(event: any) {
    const id = event.currentTarget.dataset.id as string;
    this.setData({ detailLoading: true, selected: null });
    try {
      const response = await api.approvals.get(id);
      this.setData({ selected: response.data.data || null });
    } catch (error) { wx.showToast({ title: (error as Error).message, icon: "none" }); }
    finally { this.setData({ detailLoading: false }); }
  },
  noop() {},
  closeDetail() { this.setData({ selected: null }); },
});
