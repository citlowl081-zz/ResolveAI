import { api } from "../../services/api";

Page({
  data: { items: [] as Product[], loading: true },
  async onLoad() {
    try {
      const res = await api.products.list();
      if (res.data.success && res.data.data) this.setData({ items: res.data.data.items });
    } catch (e) {} finally { this.setData({ loading: false }); }
  },
});
