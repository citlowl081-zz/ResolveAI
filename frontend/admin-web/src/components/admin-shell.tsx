"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { adminConsole } from "@/lib/api";

const menu = [
  ["/", "数据看板", "▦"],
  ["/tickets", "工单管理", "◫"],
  ["/orders", "订单管理", "▤"],
  ["/users", "用户管理", "♙"],
  ["/products", "商品管理", "◇"],
  ["/approvals", "审批中心", "✓"],
  ["/policies", "知识库管理", "▥"],
  ["/traces", "Agent 追踪", "⌁"],
  ["/tool-logs", "工具日志", "≡"],
  ["/system", "系统状态", "⚙"],
] as const;

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [service, setService] = useState<{
    backend: string;
    provider: string;
    model: string;
  } | null>(null);
  const isLogin = pathname === "/login";
  const pageTitle = useMemo(
    () =>
      menu.find(([href]) =>
        href === "/" ? pathname === "/" : pathname.startsWith(href),
      )?.[1] || "管理后台",
    [pathname],
  );

  useEffect(() => {
    setCollapsed(localStorage.getItem("admin-sidebar-collapsed") === "true");
  }, []);
  useEffect(() => {
    if (
      !loading &&
      !isLogin &&
      (!user || !["ADMIN", "OPERATOR"].includes(user.role))
    )
      router.replace("/login");
  }, [loading, isLogin, router, user]);
  useEffect(() => {
    if (user && !isLogin)
      adminConsole
        .system()
        .then((r) => setService(r.data))
        .catch(() => setService(null));
  }, [isLogin, user]);

  if (isLogin) return <>{children}</>;
  if (loading || !user)
    return (
      <div className="grid min-h-screen place-items-center text-sm text-slate-500">
        正在验证登录状态…
      </div>
    );

  const sidebar = (
    <>
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-4">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-blue-500 font-bold">
          RA
        </span>
        {!collapsed && (
          <span className="leading-tight">
            <strong className="block text-sm">ResolveAI</strong>
            <small className="text-[11px] text-slate-300">智能售后中台</small>
          </span>
        )}
      </div>
      <nav aria-label="管理后台主导航" className="space-y-1 p-3">
        {menu.map(([href, label, icon]) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={() => setDrawer(false)}
              title={label}
              className={`flex h-10 items-center gap-3 rounded-lg px-3 text-sm ${active ? "bg-[var(--sidebar-active)] text-white" : "text-slate-300 hover:bg-white/10 hover:text-white"}`}
            >
              <span aria-hidden className="w-5 text-center">
                {icon}
              </span>
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>
      <button
        className="absolute bottom-4 left-3 right-3 hidden rounded-lg border border-white/15 px-3 py-2 text-sm text-slate-300 hover:bg-white/10 lg:block"
        onClick={() => {
          const next = !collapsed;
          setCollapsed(next);
          localStorage.setItem("admin-sidebar-collapsed", String(next));
        }}
      >
        {collapsed ? "展开" : "收起侧栏"}
      </button>
    </>
  );

  return (
    <div className="min-h-screen bg-[var(--page-bg)]">
      <aside
        className={`fixed inset-y-0 left-0 z-40 hidden bg-[var(--sidebar-bg)] text-white lg:block ${collapsed ? "w-20" : "w-60"}`}
      >
        {sidebar}
      </aside>
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="关闭导航"
            className="absolute inset-0 bg-slate-950/45"
            onClick={() => setDrawer(false)}
          />
          <aside className="relative h-full w-60 bg-[var(--sidebar-bg)] text-white">
            {sidebar}
          </aside>
        </div>
      )}
      <div className={collapsed ? "lg:pl-20" : "lg:pl-60"}>
        <header className="sticky top-0 z-30 flex min-h-16 items-center justify-between border-b border-[var(--border)] bg-white px-4 md:px-6">
          <div className="flex items-center gap-3">
            <button
              aria-label="打开导航"
              className="rounded-lg border px-3 py-2 lg:hidden"
              onClick={() => setDrawer(true)}
            >
              ☰
            </button>
            <div>
              <h1 className="font-semibold">{pageTitle}</h1>
              <p className="text-xs text-slate-500">首页 / {pageTitle}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span
              className={`hidden rounded-full px-2 py-1 sm:inline ${service?.backend === "healthy" ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"}`}
            >
              后端：{service?.backend === "healthy" ? "正常" : "检测中"}
            </span>
            <span className="hidden rounded-full bg-blue-50 px-2 py-1 text-blue-700 md:inline">
              模型：{service?.provider === "mock" ? "Mock" : "Qwen"}
            </span>
            <span className="grid h-8 w-8 place-items-center rounded-full bg-slate-200 font-semibold">
              {user.full_name.slice(0, 1)}
            </span>
            <span className="hidden sm:inline">{user.full_name}</span>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-red-600"
            >
              退出登录
            </button>
          </div>
        </header>
        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
