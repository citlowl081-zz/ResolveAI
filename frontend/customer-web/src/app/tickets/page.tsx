"use client";
import { useState, useEffect } from "react";
import Navbar from "@/lib/navbar";
import { afterSales, type Ticket } from "@/lib/api";

const STATUS_MAP: Record<string, string> = {
  APPROVED: "已通过", REJECTED: "已拒绝", COMPLETED: "已完成",
  CANCELLED: "已取消", NEEDS_REVIEW: "待审核",
};

export default function TicketsPage() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    afterSales.list().then(r => {
      if (r.success && r.data) setItems(r.data.items);
    }).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, []);

  async function cancelTicket(id: string, version: number) {
    try {
      await afterSales.cancel(id, version);
      setItems(prev => prev.map(t => t.id === id ? { ...t, status: "CANCELLED" } : t));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "取消失败"); }
  }

  return (
    <div>
      <Navbar />
      <main className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">售后工单</h1>
        {loading && <p className="text-gray-500">加载中...</p>}
        {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
        <div className="space-y-3">
          {items.map(t => (
            <div key={t.id} className="p-4 bg-white rounded-lg border">
              <div className="flex justify-between items-center">
                <span className="font-mono text-sm">{t.ticket_number}</span>
                <span className="text-sm px-2 py-1 rounded bg-gray-100">{STATUS_MAP[t.status] || t.status}</span>
              </div>
              <p className="text-sm text-gray-500 mt-1">类型: {t.intent}</p>
              {t.reject_reason && <p className="text-sm text-red-500 mt-1">拒绝原因: {t.reject_reason}</p>}
              {t.status === "APPROVED" && (
                <button onClick={() => cancelTicket(t.id, t.version)}
                  className="mt-2 text-xs text-red-500 hover:underline">取消工单</button>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
