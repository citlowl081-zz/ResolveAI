"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { adminPolicies, type Policy } from "@/lib/api";
import { labelFor, formatDateTime } from "@/lib/labels";

export default function PoliciesPage() {
  const [items, setItems] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminPolicies
      .list()
      .then((r) => {
        if (r.success && r.data) setItems(r.data.items);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">知识库管理</h1>
      <p className="mb-6 text-sm text-gray-500">
        售后政策、法律法规、运营流程与风险控制
      </p>
      {loading && <p className="text-gray-500">加载中...</p>}
      <div className="space-y-2">
        {items.map((p) => (
          <Link
            href={`/policies/${encodeURIComponent(p.policy_key)}`}
            key={(p as { id?: string }).id || p.policy_key}
            className="block p-4 bg-white rounded-lg border hover:border-blue-300"
          >
            <div className="flex justify-between items-center">
              <div>
                <span className="font-mono text-sm font-semibold">
                  {p.policy_key}
                </span>
                <span className="text-xs text-gray-400 ml-2">v{p.version}</span>
              </div>
              <span
                className={`text-xs px-2 py-0.5 rounded ${p.status === "ACTIVE" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-600"}`}
              >
                {labelFor(p.status)}
              </span>
            </div>
            <p className="text-sm mt-1">{p.title}</p>
            <p className="text-xs text-gray-400 mt-1">
              {labelFor(p.category)} | 生效：{formatDateTime(p.effective_date)}
            </p>
            {p.content_summary && (
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {p.content_summary}
              </p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
