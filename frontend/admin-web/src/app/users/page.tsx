"use client";
import { useCallback, useEffect, useState } from "react";
import { adminConsole, type AdminUser } from "@/lib/api";
import { formatDateTime, friendlyError, labelFor } from "@/lib/labels";
import {
  DetailLink,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Pagination,
  SectionCard,
  StatusBadge,
} from "@/components/admin-ui";
export default function UsersPage() {
  const [items, setItems] = useState<AdminUser[]>([]),
    [page, setPage] = useState(1),
    [total, setTotal] = useState(0);
  const [query, setQuery] = useState(""),
    [role, setRole] = useState(""),
    [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    setLoading(true);
    adminConsole
      .users(page, query, role)
      .then((r) => {
        setItems(r.data.items);
        setTotal(r.data.total);
        setError("");
      })
      .catch((e) => setError(friendlyError(e)))
      .finally(() => setLoading(false));
  }, [page, query, role]);
  useEffect(load, [load]);
  return (
    <>
      <PageHeader title="用户管理" description="隐私安全的只读用户概览" />
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          aria-label="搜索用户"
          placeholder="姓名或邮箱"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
          className="rounded-md border px-3 py-2 text-sm"
        />
        <select
          aria-label="用户角色"
          value={role}
          onChange={(e) => {
            setRole(e.target.value);
            setPage(1);
          }}
          className="rounded-md border px-3 py-2 text-sm"
        >
          <option value="">全部角色</option>
          <option value="CUSTOMER">顾客</option>
          <option value="OPERATOR">运营人员</option>
          <option value="ADMIN">管理员</option>
        </select>
      </div>
      {error ? (
        <ErrorState message={error} retry={load} />
      ) : (
        <SectionCard>
          {loading ? (
            <LoadingState />
          ) : items.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[950px] text-left text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    {[
                      "用户 ID",
                      "姓名",
                      "邮箱",
                      "角色",
                      "订单",
                      "工单",
                      "Memory",
                      "风险",
                      "注册时间",
                      "状态",
                      "操作",
                    ].map((x) => (
                      <th key={x} className="p-3">
                        {x}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {items.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50">
                      <td className="p-3 font-mono text-xs">
                        {u.id.slice(0, 8)}…
                      </td>
                      <td className="p-3">{u.full_name}</td>
                      <td className="p-3">{u.email}</td>
                      <td className="p-3">{labelFor(u.role)}</td>
                      <td className="p-3">{u.order_count}</td>
                      <td className="p-3">{u.ticket_count}</td>
                      <td className="p-3">{u.memory_count}</td>
                      <td className="p-3">
                        <StatusBadge value={u.risk_level} />
                      </td>
                      <td className="p-3">{formatDateTime(u.created_at)}</td>
                      <td className="p-3">{u.is_active ? "正常" : "停用"}</td>
                      <td className="p-3">
                        <DetailLink href={`/users/${u.id}`} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState />
          )}
          <Pagination
            page={page}
            total={total}
            pageSize={20}
            onChange={setPage}
          />
        </SectionCard>
      )}
    </>
  );
}
