"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { adminToolLogs, type ToolLog } from "@/lib/api";

export default function ToolLogsPage() {
  const [items, setItems] = useState<ToolLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminToolLogs.list(page).then(r => { if (r.success && r.data) { setItems(r.data.items); setTotal(r.data.total); } }).finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-gray-800 text-white px-6 py-3"><Link href="/" className="font-bold">ResolveAI Admin</Link></nav>
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Tool Logs ({total})</h1>
        {loading && <p className="text-gray-500">加载中...</p>}
        <div className="overflow-x-auto">
          <table className="w-full bg-white rounded-lg border">
            <thead><tr className="border-b bg-gray-50 text-left text-sm text-gray-600">
              <th className="p-3">时间</th><th className="p-3">Tool</th><th className="p-3">成功</th><th className="p-3">耗时(ms)</th><th className="p-3">错误</th>
            </tr></thead>
            <tbody>
              {items.map(l => (
                <tr key={l.id} className="border-b text-sm">
                  <td className="p-3 text-gray-400">{l.created_at ? new Date(l.created_at).toLocaleTimeString() : "-"}</td>
                  <td className="p-3 font-mono text-xs">{l.tool_name}</td>
                  <td className="p-3">{l.is_success ? <span className="text-green-600">✓</span> : <span className="text-red-600">✗</span>}</td>
                  <td className="p-3">{l.duration_ms}</td>
                  <td className="p-3 text-red-500 text-xs max-w-xs truncate">{l.error_message || "-"}</td>
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
