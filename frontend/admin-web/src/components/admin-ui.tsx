import Link from "next/link";
import { labelFor } from "@/lib/labels";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-2xl font-bold">{title}</h2>
        {description && (
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}
export function SectionCard({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-lg border border-[var(--border)] bg-white shadow-sm ${className}`}
    >
      {title && <h3 className="border-b px-5 py-4 font-semibold">{title}</h3>}
      {children}
    </section>
  );
}
export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}
export function StatusBadge({ value }: { value: string | null | undefined }) {
  const v = value || "";
  const color = /FAILED|REJECTED|CANCELLED/.test(v)
    ? "bg-red-50 text-red-700"
    : /APPROVED|ACTIVE|COMPLETED|DELIVERED|PAID/.test(v)
      ? "bg-green-50 text-green-700"
      : /PENDING|REVIEW|MEDIUM/.test(v)
        ? "bg-amber-50 text-amber-700"
        : /HIGH|CRITICAL/.test(v)
          ? "bg-red-50 text-red-700"
          : "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs ${color}`}>
      {labelFor(v)}
    </span>
  );
}
export function LoadingState({ text = "正在加载数据…" }: { text?: string }) {
  return (
    <div className="animate-pulse p-10 text-center text-sm text-slate-500">
      {text}
    </div>
  );
}
export function EmptyState({
  title = "暂无数据",
  description = "当前筛选条件下没有可展示的记录。",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="p-12 text-center">
      <p className="font-medium text-slate-700">{title}</p>
      <p className="mt-1 text-sm text-slate-400">{description}</p>
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      <p>{message}</p>
      {retry && (
        <button
          onClick={retry}
          className="mt-3 rounded-md bg-red-600 px-3 py-1.5 text-white"
        >
          重新加载
        </button>
      )}
    </div>
  );
}
export function Pagination({
  page,
  total,
  pageSize,
  onChange,
}: {
  page: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-end gap-3 border-t px-4 py-3 text-sm">
      <span className="text-slate-500">
        共 {total.toLocaleString("zh-CN")} 条，第 {page}/{pages} 页
      </span>
      <button
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        className="rounded-md border px-3 py-1.5 disabled:opacity-40"
      >
        上一页
      </button>
      <button
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
        className="rounded-md border px-3 py-1.5 disabled:opacity-40"
      >
        下一页
      </button>
    </div>
  );
}
export function DetailLink({ href }: { href: string }) {
  return (
    <Link
      className="text-sm font-medium text-blue-600 hover:text-blue-800"
      href={href}
    >
      查看详情
    </Link>
  );
}
