import { api } from "../../services/api";

Page({
  data: { product: null as Product | null, loading: true },
  async onLoad(options: any) {
    if (!options.id) return;
    try {
      const res = await api.products.get(options.id);
      if (res.data.success && res.data.data) this.setData({ product: res.data.data });
    } catch (e) {} finally { this.setData({ loading: false }); }
  },
});
