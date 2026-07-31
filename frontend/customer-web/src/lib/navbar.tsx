"use client";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
const links = [
  ["/products", "精选商品"],
  ["/orders", "订单中心"],
  ["/agent", "AI 售后助手"],
  ["/tickets", "售后服务"],
  ["/memories", "偏好记忆"],
  ["/approvals", "审批状态"],
  ["/account", "用户中心"],
] as const;
export default function Navbar() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <nav className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4 md:px-6">
        <Link href="/" className="flex items-center gap-2 font-bold">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-blue-600 text-sm text-white">
            RA
          </span>
          <span>ResolveAI 智选商城</span>
        </Link>
        <button
          aria-label="打开导航"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="rounded-md border px-3 py-2 lg:hidden"
        >
          ☰
        </button>
        {user && (
          <div className="hidden items-center gap-5 lg:flex">
            {links.map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className="text-sm text-slate-600 hover:text-blue-700"
              >
                {label}
              </Link>
            ))}
          </div>
        )}
        <div className="hidden items-center gap-3 text-sm lg:flex">
          {user ? (
            <>
              <Link
                href="/account"
                className="grid h-8 w-8 place-items-center rounded-full bg-blue-50 font-semibold text-blue-700"
                title={user.full_name}
              >
                {user.full_name.slice(0, 1)}
              </Link>
              <button onClick={logout} className="text-red-600">
                退出登录
              </button>
            </>
          ) : (
            <>
              <Link href="/login">登录</Link>
              <Link
                href="/register"
                className="rounded-md bg-blue-600 px-4 py-2 text-white"
              >
                注册
              </Link>
            </>
          )}
        </div>
      </div>
      {open && (
        <div className="border-t bg-white px-4 py-4 lg:hidden">
          <div className="grid gap-1">
            {user ? (
              links.map(([href, label]) => (
                <Link
                  onClick={() => setOpen(false)}
                  key={href}
                  href={href}
                  className="rounded-md px-3 py-2 text-sm hover:bg-slate-50"
                >
                  {label}
                </Link>
              ))
            ) : (
              <>
                <Link href="/login" className="px-3 py-2">
                  登录
                </Link>
                <Link href="/register" className="px-3 py-2">
                  注册
                </Link>
              </>
            )}
            {user && (
              <button
                onClick={logout}
                className="px-3 py-2 text-left text-sm text-red-600"
              >
                退出登录
              </button>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
