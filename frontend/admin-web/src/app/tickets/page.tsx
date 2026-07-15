"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { adminTickets, type Ticket } from "@/lib/api";

const STATUS_MAP: Record<string, string> = { APPROVED: "已通过", REJECTED: "已拒绝", COMPLETED: "已完成", CANCELLED: "已取消", NEEDS_REVIEW: "待审核" };

export default function AdminTicketsPage() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminTickets.list(page, status || undefined).then(r => {
      if (r.success && r.data) { setItems(r.data.items); setTotal(r.data.total); }
    }).finally(() => setLoading(false));
  }, [page, status]);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-gray-800 text-white px-6 py-3"><Link href="/" className="font-bold">ResolveAI Admin</Link></nav>
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">工单管理 ({total})</h1>
        <div className="flex gap-3 mb-4">
          {["", "NEEDS_REVIEW", "APPROVED", "COMPLETED", "REJECTED"].map(s => (
            <button key={s} onClick={() => { setStatus(s); setPage(1); }} className={`px-3 py-1 rounded text-sm ${status === s ? "bg-blue-600 text-white" : "bg-white border"}`}>{s || "全部"}</button>
          ))}
        </div>
        {loading && <p className="text-gray-500">加载中...</p>}
        <div className="space-y-2">
          {items.map(t => (
            <Link key={t.id} href={`/tickets/${t.id}`} className="block p-4 bg-white rounded-lg border hover:shadow-sm">
              <div className="flex justify-between items-center">
                <span className="font-mono text-sm">{t.ticket_number}</span>
                <span className="text-sm px-2 py-0.5 rounded bg-gray-100">{STATUS_MAP[t.status] || t.status}</span>
              </div>
              <p className="text-sm text-gray-500 mt-1">类型: {t.intent} | 订单: {t.order_id?.slice(0, 8)}...</p>
            </Link>
          ))}
        </div>
        {total > 20 && (
          <div className="flex gap-2 mt-4 justify-center">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="px-3 py-1 border rounded disabled:opacity-30">上一页</button>
            <span className="px-3 py-1 text-sm text-gray-500">第 {page} 页</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page * 20 >= total} className="px-3 py-1 border rounded disabled:opacity-30">下一页</button>
          </div>
        )}
      </main>
    </div>
  );
}
