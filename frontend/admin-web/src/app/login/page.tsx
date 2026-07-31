"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { friendlyError } from "@/lib/labels";
export default function AdminLoginPage() {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      router.push("/");
    } catch (e) {
      setError(friendlyError(e));
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden bg-[var(--sidebar-bg)] p-16 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-4">
          <span className="grid h-12 w-12 place-items-center rounded-lg bg-blue-500 text-lg font-bold">
            RA
          </span>
          <div>
            <h1 className="text-2xl font-bold">ResolveAI 智能售后中台</h1>
            <p className="mt-1 text-slate-300">智能售后运营与风险控制平台</p>
          </div>
        </div>
        <div>
          <p className="max-w-xl text-3xl font-semibold leading-relaxed">
            让售后政策、Agent 决策与人工审批在同一个安全工作台中清晰协同。
          </p>
          <p className="mt-4 text-sm text-slate-300">
            Demo 环境 · 仅使用演示账号
          </p>
        </div>
      </section>
      <section className="grid place-items-center p-6">
        <form
          onSubmit={submit}
          className="w-full max-w-sm rounded-lg border bg-white p-8 shadow-sm"
        >
          <div className="mb-7 lg:hidden">
            <span className="font-bold">ResolveAI 智能售后中台</span>
            <p className="mt-1 text-sm text-slate-500">
              智能售后运营与风险控制平台
            </p>
          </div>
          <h2 className="text-2xl font-bold">管理员登录</h2>
          <p className="mt-2 text-sm text-slate-500">
            请输入 Demo 管理员或运营人员账号
          </p>
          {error && (
            <div
              role="alert"
              className="mt-5 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              {error}
            </div>
          )}
          <label className="mt-6 block text-sm font-medium">
            邮箱
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-2 w-full rounded-md border px-3 py-2.5"
              placeholder="admin@example.com"
              required
            />
          </label>
          <label className="mt-4 block text-sm font-medium">
            密码
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-2 w-full rounded-md border px-3 py-2.5"
              required
            />
          </label>
          <button
            disabled={loading}
            className="mt-6 w-full rounded-md bg-[var(--primary)] py-2.5 font-medium text-white disabled:opacity-50"
          >
            {loading ? "正在登录…" : "登录"}
          </button>
          <p className="mt-5 text-center text-xs text-slate-400">
            账号信息请查看项目 README 的 Demo 登录说明
          </p>
        </form>
      </section>
    </div>
  );
}
