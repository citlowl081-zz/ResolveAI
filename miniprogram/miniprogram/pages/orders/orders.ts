import { api } from "../../services/api";
import { STATUS_MAP } from "../../utils/util";

Page({
  data: { items: [] as Order[], loading: true, error: "", statusText: STATUS_MAP },
  async onLoad() {
    try {
      const res = await api.orders.list();
      if (res.data.success && res.data.data) this.setData({ items: res.data.data.items });
    } catch (error) { this.setData({ error: (error as Error).message }); }
    finally { this.setData({ loading: false }); }
  },
});
