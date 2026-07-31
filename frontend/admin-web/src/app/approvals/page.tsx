"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { adminApprovals, type ApprovalTask } from "@/lib/api";
import { labelFor, friendlyError } from "@/lib/labels";

export default function AdminApprovalsPage() {
  const [items, setItems] = useState<ApprovalTask[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("PENDING");
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await adminApprovals.list(page, status);
      if (r.success && r.data) {
        setItems(r.data.items);
        setTotal(r.data.total);
      }
    } finally {
      setLoading(false);
    }
  }, [page, status]);
  useEffect(() => {
    load();
  }, [load]);

  async function approve(id: string, version: number) {
    const reason = prompt("批准理由 (可选):") || "";
    try {
      await adminApprovals.approve(id, version, reason, crypto.randomUUID());
      setActionMsg("已批准");
      load();
    } catch (e: unknown) {
      alert(friendlyError(e));
    }
  }

  async function reject(id: string, version: number) {
    const reason = prompt("拒绝理由:") || "";
    if (!reason) return;
    try {
      await adminApprovals.reject(id, version, reason, crypto.randomUUID());
      setActionMsg("已拒绝");
      load();
    } catch (e: unknown) {
      alert(friendlyError(e));
    }
  }

  async function execute(id: string) {
    try {
      const r = await adminApprovals.execute(id, crypto.randomUUID());
      setActionMsg(r.success ? "执行成功" : "执行失败");
      load();
    } catch (e: unknown) {
      alert(friendlyError(e));
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">审批中心 ({total})</h1>
      {actionMsg && (
        <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-4 text-sm">
          {actionMsg}
        </div>
      )}
      <div className="flex gap-3 mb-4">
        {["PENDING", "APPROVED", "REJECTED"].map((s) => (
          <button
            key={s}
            onClick={() => {
              setStatus(s);
              setPage(1);
            }}
            className={`px-3 py-1 rounded text-sm ${status === s ? "bg-blue-600 text-white" : "bg-white border"}`}
          >
            {labelFor(s)}
          </button>
        ))}
      </div>
      {loading && <p className="text-gray-500">加载中...</p>}
      <div className="space-y-3">
        {items.map((a) => (
          <div key={a.id} className="p-4 bg-white rounded-lg border">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs text-gray-400">
                ID: {a.id.slice(0, 12)}...
              </span>
              <span
                className={`text-sm px-2 py-0.5 rounded ${a.status === "PENDING" ? "bg-yellow-50 text-yellow-700" : a.status === "APPROVED" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}
              >
                {labelFor(a.status)}
              </span>
            </div>
            <div className="mt-2 text-sm">
              <p>
                类型：
                <span className="font-semibold">
                  {labelFor(a.approval_type)}
                </span>{" "}
                | 用户：{a.user_id?.slice(0, 8)}... | 操作：
                {labelFor(a.tool_name)}
              </p>
              <p>风险：{labelFor(a.risk_level)}</p>
              {a.reason && (
                <p className="text-gray-500 text-xs mt-1">原因: {a.reason}</p>
              )}
            </div>
            {a.status === "PENDING" && (
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => approve(a.id, a.version)}
                  className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                >
                  批准
                </button>
                <button
                  onClick={() => reject(a.id, a.version)}
                  className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
                >
                  拒绝
                </button>
              </div>
            )}
            {a.status === "APPROVED" && (
              <button
                onClick={() => execute(a.id)}
                className="mt-3 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                执行操作
              </button>
            )}
            <Link
              href={`/approvals/${a.id}`}
              className="ml-3 text-sm text-blue-600"
            >
              查看详情
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
