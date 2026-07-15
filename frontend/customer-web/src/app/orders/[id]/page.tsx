"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Navbar from "@/lib/navbar";
import { orders, logistics, type Order, type LogisticsInfo } from "@/lib/api";

const STATUS_MAP: Record<string, string> = {
  PENDING_PAYMENT: "待支付", PAID: "已支付", SHIPPED: "已发货",
  DELIVERED: "已签收", CANCELLED: "已取消", REFUNDED: "已退款",
};

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [log, setLog] = useState<LogisticsInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    orders.get(id).then(r => {
      if (r.success && r.data) setOrder(r.data);
    }).finally(() => setLoading(false));
    logistics.get(id).then(r => {
      if (r.success && r.data) setLog(r.data);
    }).catch(() => {});
  }, [id]);

  return (
    <div>
      <Navbar />
      <main className="max-w-2xl mx-auto p-6">
        {loading && <p className="text-gray-500">加载中...</p>}
        {order && (
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div className="flex justify-between">
              <h1 className="text-xl font-bold">订单 {order.order_number}</h1>
              <span className="px-2 py-1 rounded bg-blue-50 text-blue-700 text-sm">{STATUS_MAP[order.status] || order.status}</span>
            </div>
            <div className="text-sm text-gray-600 space-y-1">
              <p>总金额: ¥{order.total_amount}</p>
              <p>运费: ¥{order.shipping_fee}</p>
              {order.paid_at && <p>支付时间: {new Date(order.paid_at).toLocaleString()}</p>}
              {order.shipped_at && <p>发货时间: {new Date(order.shipped_at).toLocaleString()}</p>}
              {order.delivered_at && <p>签收时间: {new Date(order.delivered_at).toLocaleString()}</p>}
            </div>
            <h3 className="font-semibold mt-4">商品明细</h3>
            {order.items?.map((item, i) => (
              <div key={i} className="flex justify-between text-sm border-b pb-2">
                <span>{item.product_name} × {item.quantity}</span>
                <span>¥{item.unit_price}</span>
              </div>
            ))}
            {log && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold mb-2">物流信息</h3>
                <p className="text-sm">{log.carrier}: {log.tracking_number}</p>
                <p className="text-sm text-gray-500">状态: {log.status}</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
