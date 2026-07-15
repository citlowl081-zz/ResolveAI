import { api } from "../../services/api";
import { STATUS_MAP } from "../../utils/util";

Page({
  data: { order: null as Order | null, logistics: null as LogisticsInfo | null, loading: true, statusText: STATUS_MAP },
  async onLoad(options: any) {
    if (!options.id) return;
    try {
      const [oRes, lRes] = await Promise.all([api.orders.get(options.id), api.logistics.get(options.id).catch(() => null)]);
      if (oRes.data.success && oRes.data.data) this.setData({ order: oRes.data.data });
      if (lRes && lRes.data.success && lRes.data.data) this.setData({ logistics: lRes.data.data });
    } catch (e) {} finally { this.setData({ loading: false }); }
  },
});
