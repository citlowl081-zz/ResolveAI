"use client";
import { useState, useEffect } from "react";
import Navbar from "@/lib/navbar";
import { approvals, type ApprovalTask } from "@/lib/api";

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    approvals.list().then(r => {
      if (r.success && r.data) setItems(r.data.items);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <Navbar />
      <main className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">审批状态</h1>
        {loading && <p className="text-gray-500">加载中...</p>}
        <div className="space-y-3">
          {items.map(a => (
            <div key={a.id} className="p-4 bg-white rounded-lg border">
              <div className="flex justify-between items-center">
                <span className="font-mono text-xs text-gray-400">ID: {a.id.slice(0, 8)}...</span>
                <span className={`text-sm px-2 py-0.5 rounded ${a.status === "PENDING" ? "bg-yellow-50 text-yellow-700" : a.status === "APPROVED" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>{a.status}</span>
              </div>
              <div className="mt-2 text-sm space-y-1">
                <p>类型: <span className="font-semibold">{a.approval_type}</span> | 操作: {a.tool_name}</p>
                <p>风险级别: {a.risk_level}</p>
                {a.reason && <p className="text-gray-500">原因: {a.reason}</p>}
                {a.decision_reason && <p className="text-gray-500">决定: {a.decision_reason}</p>}
              </div>
            </div>
          ))}
        </div>
        {!loading && items.length === 0 && <p className="text-gray-400">暂无审批</p>}
      </main>
    </div>
  );
}
