"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { adminTickets, type Ticket } from "@/lib/api";

export default function AdminTicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    adminTickets.get(id)
      .then(r => { if (r.success && r.data) setTicket(r.data); })
      .catch(e => setError(e instanceof Error ? e.message : "加载失败"));
  }, [id]);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-gray-800 text-white px-6 py-3">
        <Link href="/tickets" className="font-bold">← 工单管理</Link>
      </nav>
      <main className="max-w-3xl mx-auto p-6">
        {error && <p className="text-red-600">{error}</p>}
        {!ticket && !error && <p className="text-gray-500">加载中...</p>}
        {ticket && (
          <div className="bg-white border rounded-xl p-6 space-y-3">
            <h1 className="text-2xl font-bold">{ticket.ticket_number}</h1>
            <p>状态: {ticket.status}</p>
            <p>类型: {ticket.intent}</p>
            <p className="font-mono text-sm">订单: {ticket.order_id}</p>
            <p>版本: v{ticket.version}</p>
            {ticket.reject_reason && (
              <p className="text-red-600">拒绝原因: {ticket.reject_reason}</p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
