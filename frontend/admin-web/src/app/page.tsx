"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { adminTickets, adminApprovals } from "@/lib/api";

export default function AdminDashboard() {
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [ticketTotal, setTicketTotal] = useState(0);
  const [pendingApprovals, setPendingApprovals] = useState(0);

  useEffect(() => {
    if (!authLoading && !user) { router.push("/login"); return; }
    if (!authLoading && user && user.role !== "ADMIN" && user.role !== "OPERATOR") { router.push("/login"); return; }
    adminTickets.list(1).then(r => { if (r.success && r.data) setTicketTotal(r.data.total); }).catch(() => {});
    adminApprovals.list(1, "PENDING").then(r => { if (r.success && r.data) setPendingApprovals(r.data.total); }).catch(() => {});
  }, [authLoading, user, router]);

  if (authLoading) return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-500">加载中...</p></div>;
  if (!user) return null;

  return (
    <div className="min-h-screen">
      <nav className="bg-gray-800 text-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-bold text-lg">ResolveAI Admin</Link>
          <div className="flex gap-4 text-sm text-gray-300">
            <Link href="/tickets" className="hover:text-white">工单</Link>
            <Link href="/approvals" className="hover:text-white">审批</Link>
            <Link href="/policies" className="hover:text-white">政策</Link>
            <Link href="/traces" className="hover:text-white">Trace</Link>
            <Link href="/tool-logs" className="hover:text-white">Tool Log</Link>
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-400">{user.full_name} ({user.role})</span>
          <button onClick={logout} className="text-red-400 hover:text-red-300">退出</button>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl border p-6"><p className="text-3xl font-bold">{ticketTotal}</p><p className="text-gray-500 text-sm mt-1">售后工单总数</p></div>
          <div className="bg-yellow-50 rounded-xl border p-6"><p className="text-3xl font-bold text-yellow-700">{pendingApprovals}</p><p className="text-gray-500 text-sm mt-1">待审批</p></div>
          <div className="bg-white rounded-xl border p-6"><p className="text-3xl font-bold">—</p><p className="text-gray-500 text-sm mt-1">Agent 会话</p></div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[{ href: "/tickets", label: "工单管理", desc: "查看和处理售后工单" }, { href: "/approvals", label: "审批中心", desc: "批准或拒绝高风险操作" }, { href: "/policies", label: "政策管理", desc: "管理售后政策文档" }, { href: "/traces", label: "Agent Trace", desc: "查看 Agent 执行轨迹" }, { href: "/tool-logs", label: "Tool Log", desc: "工具调用日志" }].map(item => (
            <Link key={item.href} href={item.href} className="p-4 bg-white rounded-lg border hover:border-blue-400 hover:shadow transition-all">
              <h3 className="font-semibold">{item.label}</h3><p className="text-sm text-gray-500 mt-1">{item.desc}</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
