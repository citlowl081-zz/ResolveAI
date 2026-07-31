import { api } from "../../services/api";
import { STATUS_MAP } from "../../utils/util";

Page({
  data: {
    order: null as Order | null, logistics: null as LogisticsInfo | null,
    logisticsAvailable: false, logisticsLoading: false, loading: true,
    error: "", statusText: STATUS_MAP,
  },
  async onLoad(options: any) {
    if (!options.id) return;
    try {
      const orderResponse = await api.orders.get(options.id);
      const order = orderResponse.data.data;
      if (!order) return;
      const logisticsAvailable = ["SHIPPED", "DELIVERED"].includes(order.status);
      this.setData({ order, logisticsAvailable });
      if (logisticsAvailable) await this.loadLogistics(order.id);
    } catch (error) {
      this.setData({ error: (error as Error).message });
    } finally { this.setData({ loading: false }); }
  },
  async loadLogistics(orderId: string) {
    this.setData({ logisticsLoading: true });
    try {
      const response = await api.logistics.get(orderId);
      this.setData({ logistics: response.data.data || null });
    } catch (error) {
      if ((error as Error).message !== "未找到对应数据") this.setData({ error: (error as Error).message });
    } finally { this.setData({ logisticsLoading: false }); }
  },
});
