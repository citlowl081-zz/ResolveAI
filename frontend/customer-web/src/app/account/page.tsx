"use client";
import Navbar from "@/lib/navbar";
import { useAuth } from "@/lib/auth-context";
export default function AccountPage() {
  const { user, loading } = useAuth();
  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-4xl p-5 md:p-8">
        <h1 className="text-3xl font-bold">用户中心</h1>
        <p className="mt-2 text-slate-500">查看当前账号资料与常用服务入口</p>
        <section className="mt-6 rounded-lg border bg-white p-6">
          {loading ? (
            <p>正在加载用户资料…</p>
          ) : user ? (
            <dl className="grid gap-5 sm:grid-cols-2">
              <div>
                <dt className="text-sm text-slate-500">姓名</dt>
                <dd className="mt-1 font-medium">{user.full_name}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">邮箱</dt>
                <dd className="mt-1">{user.email}</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">账号角色</dt>
                <dd className="mt-1">顾客</dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500">资料维护</dt>
                <dd className="mt-1 text-slate-500">
                  当前版本暂不支持在线修改
                </dd>
              </div>
            </dl>
          ) : null}
        </section>
      </main>
    </>
  );
}
