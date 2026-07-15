"use client";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function Navbar() {
  const { user, logout } = useAuth();
  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <Link href="/" className="font-bold text-lg text-blue-600">ResolveAI</Link>
        {user && (
          <div className="flex gap-4 text-sm">
            <Link href="/products" className="text-gray-600 hover:text-gray-900">商品</Link>
            <Link href="/orders" className="text-gray-600 hover:text-gray-900">订单</Link>
            <Link href="/agent" className="text-gray-600 hover:text-gray-900">客服</Link>
            <Link href="/tickets" className="text-gray-600 hover:text-gray-900">售后</Link>
            <Link href="/memories" className="text-gray-600 hover:text-gray-900">记忆</Link>
            <Link href="/approvals" className="text-gray-600 hover:text-gray-900">审批</Link>
          </div>
        )}
      </div>
      {user && (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-700">{user.full_name}</span>
          <button onClick={logout} className="text-red-500 hover:text-red-700">退出</button>
        </div>
      )}
    </nav>
  );
}
