"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import Navbar from "@/lib/navbar";
import { orders, type Order } from "@/lib/api";

const STATUS_MAP: Record<string, string> = {
  PENDING_PAYMENT: "待支付", PAID: "已支付", SHIPPED: "已发货",
  DELIVERED: "已签收", CANCELLED: "已取消", REFUNDED: "已退款",
};

export default function OrdersPage() {
  const [items, setItems] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    orders.list().then(r => {
      if (r.success && r.data) setItems(r.data.items);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <Navbar />
      <main className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">我的订单</h1>
        {loading && <p className="text-gray-500">加载中...</p>}
        <div className="space-y-3">
          {items.map(o => (
            <Link key={o.id} href={`/orders/${o.id}`} className="block p-4 bg-white rounded-lg border hover:shadow-md">
              <div className="flex justify-between items-center">
                <span className="font-mono text-sm">{o.order_number}</span>
                <span className="text-sm px-2 py-1 rounded bg-gray-100">{STATUS_MAP[o.status] || o.status}</span>
              </div>
              <p className="text-lg font-bold mt-1">¥{o.total_amount}</p>
              <p className="text-xs text-gray-400 mt-1">{o.items?.length || 0} 件商品</p>
            </Link>
          ))}
        </div>
        {!loading && items.length === 0 && <p className="text-gray-400">暂无订单</p>}
      </main>
    </div>
  );
}
