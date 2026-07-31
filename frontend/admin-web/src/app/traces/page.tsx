"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { adminTraces, type AgentTrace } from "@/lib/api";
import { labelFor, formatDateTime, formatDuration } from "@/lib/labels";

export default function TracesPage() {
  const [items, setItems] = useState<AgentTrace[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    adminTraces
      .list(page)
      .then((r) => {
        if (r.success && r.data) {
          setItems(r.data.items);
          setTotal(r.data.total);
        }
      })
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Agent 追踪 ({total})</h1>
      {loading && <p className="text-gray-500">加载中...</p>}
      <div className="overflow-x-auto">
        <table className="w-full bg-white rounded-lg border">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-sm text-gray-600">
              <th className="p-3">时间</th>
              <th className="p-3">节点</th>
              <th className="p-3">路由 / 模型服务</th>
              <th className="p-3">工具</th>
              <th className="p-3">耗时</th>
              <th className="p-3">成功</th>
              <th className="p-3">错误</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} className="border-b text-sm">
                <td className="p-3 text-gray-400">
                  {formatDateTime(t.created_at)}
                </td>
                <td className="p-3">
                  <div>{labelFor(t.node_name)}</div>
                  <small className="font-mono text-gray-400">
                    技术标识：{t.node_name}
                  </small>
                </td>
                <td className="p-3 text-xs">
                  <div>{t.routing_decision || "-"}</div>
                  {t.llm_call && (
                    <div className="text-gray-500">
                      模型服务：{String(t.llm_call.provider || "-")}
                      {" · "}真实调用成功：
                      {String(t.llm_call.real_llm_success ?? "-")}
                      {" · "}使用降级：
                      {String(t.llm_call.fallback_used ?? false)}
                    </div>
                  )}
                </td>
                <td className="p-3 text-xs font-mono">
                  {t.tool_calls_summary
                    ?.map((call) => labelFor(String(call.selected_tool || "-")))
                    .join("、") || "-"}
                </td>
                <td className="p-3">{formatDuration(t.duration_ms)}</td>
                <td className="p-3">
                  {t.is_success ? (
                    <span className="text-green-600">✓</span>
                  ) : (
                    <span className="text-red-600">✗</span>
                  )}
                </td>
                <td className="p-3 text-red-500 text-xs">
                  <div>{t.error_code || "-"}</div>
                  <Link
                    className="text-blue-600"
                    href={`/traces/${t.trace_id}`}
                  >
                    查看详情
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total > 50 && (
        <div className="flex gap-2 mt-4 justify-center">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1 border rounded disabled:opacity-30"
          >
            上一页
          </button>
          <span className="px-3 py-1 text-sm">第 {page} 页</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 50 >= total}
            className="px-3 py-1 border rounded disabled:opacity-30"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}
