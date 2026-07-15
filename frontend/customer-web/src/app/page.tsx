"use client";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import Navbar from "@/lib/navbar";

export default function Home() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-500">加载中...</p></div>;
  if (!user) return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-white">
      <div className="text-center max-w-md p-8">
        <h1 className="text-3xl font-bold text-blue-600 mb-2">ResolveAI</h1>
        <p className="text-gray-500 mb-8">AI 驱动的电商售后智能客服</p>
        <div className="flex gap-4 justify-center">
          <Link href="/login" className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">登录</Link>
          <Link href="/register" className="px-6 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50">注册</Link>
        </div>
      </div>
    </div>
  );
  return (
    <div>
      <Navbar />
      <main className="max-w-4xl mx-auto p-6">
        <h2 className="text-2xl font-bold mb-4">欢迎, {user.full_name}</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { href: "/products", label: "浏览商品", desc: "查看商品列表" },
            { href: "/orders", label: "我的订单", desc: "查看订单状态" },
            { href: "/agent", label: "智能客服", desc: "AI 售后助手" },
            { href: "/tickets", label: "售后服务", desc: "查看售后工单" },
            { href: "/memories", label: "我的记忆", desc: "长期偏好管理" },
            { href: "/approvals", label: "审批状态", desc: "人工审批进度" },
          ].map(item => (
            <Link key={item.href} href={item.href} className="p-4 bg-white rounded-lg border hover:border-blue-400 hover:shadow transition-all">
              <h3 className="font-semibold text-gray-800">{item.label}</h3>
              <p className="text-sm text-gray-500 mt-1">{item.desc}</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
