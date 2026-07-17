"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { adminTraces, type AgentTrace } from "@/lib/api";

export default function TracesPage() {
  const [items, setItems] = useState<AgentTrace[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminTraces.list(page).then(r => { if (r.success && r.data) { setItems(r.data.items); setTotal(r.data.total); } }).finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-gray-800 text-white px-6 py-3"><Link href="/" className="font-bold">ResolveAI Admin</Link></nav>
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Agent Traces ({total})</h1>
        {loading && <p className="text-gray-500">加载中...</p>}
        <div className="overflow-x-auto">
          <table className="w-full bg-white rounded-lg border">
            <thead><tr className="border-b bg-gray-50 text-left text-sm text-gray-600">
              <th className="p-3">时间</th><th className="p-3">Node</th><th className="p-3">路由 / Provider</th><th className="p-3">Tool</th><th className="p-3">耗时(ms)</th><th className="p-3">成功</th><th className="p-3">错误</th>
            </tr></thead>
            <tbody>
              {items.map(t => (
                <tr key={t.id} className="border-b text-sm">
                  <td className="p-3 text-gray-400">{t.created_at ? new Date(t.created_at).toLocaleTimeString() : "-"}</td>
                  <td className="p-3 font-mono">{t.node_name}</td>
                  <td className="p-3 text-xs">
                    <div>{t.routing_decision || "-"}</div>
                    {t.llm_call && (
                      <div className="text-gray-500">
                        provider={String(t.llm_call.provider || "-")}
                        {" · "}success={String(t.llm_call.real_llm_success ?? "-")}
                        {" · "}fallback={String(t.llm_call.fallback_used ?? false)}
                      </div>
                    )}
                  </td>
                  <td className="p-3 text-xs font-mono">
                    {t.tool_calls_summary?.map(call => String(call.selected_tool || "-")).join(", ") || "-"}
                  </td>
                  <td className="p-3">{t.duration_ms}</td>
                  <td className="p-3">{t.is_success ? <span className="text-green-600">✓</span> : <span className="text-red-600">✗</span>}</td>
                  <td className="p-3 text-red-500 text-xs">{t.error_code || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > 50 && (
          <div className="flex gap-2 mt-4 justify-center">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="px-3 py-1 border rounded disabled:opacity-30">上一页</button>
            <span className="px-3 py-1 text-sm">第 {page} 页</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page * 50 >= total} className="px-3 py-1 border rounded disabled:opacity-30">下一页</button>
          </div>
        )}
      </main>
    </div>
  );
}
