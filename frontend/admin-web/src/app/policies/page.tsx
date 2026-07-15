"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { adminPolicies, type Policy } from "@/lib/api";

export default function PoliciesPage() {
  const [items, setItems] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminPolicies.list().then(r => { if (r.success && r.data) setItems(r.data.items); }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-gray-800 text-white px-6 py-3"><Link href="/" className="font-bold">ResolveAI Admin</Link></nav>
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">政策管理</h1>
        {loading && <p className="text-gray-500">加载中...</p>}
        <div className="space-y-2">
          {items.map(p => (
            <div key={(p as { id?: string }).id || p.policy_key} className="p-4 bg-white rounded-lg border">
              <div className="flex justify-between items-center">
                <div>
                  <span className="font-mono text-sm font-semibold">{p.policy_key}</span>
                  <span className="text-xs text-gray-400 ml-2">v{p.version}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${p.status === "ACTIVE" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-600"}`}>{p.status}</span>
              </div>
              <p className="text-sm mt-1">{p.title}</p>
              <p className="text-xs text-gray-400 mt-1">{p.category} | 生效: {p.effective_date}</p>
              {p.content_summary && <p className="text-xs text-gray-500 mt-1 line-clamp-2">{p.content_summary}</p>}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
