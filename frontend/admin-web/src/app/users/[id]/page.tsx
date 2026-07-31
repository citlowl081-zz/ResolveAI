"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminConsole, type AdminUserDetail } from "@/lib/api";
import { formatDateTime, friendlyError, labelFor } from "@/lib/labels";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/admin-ui";
export default function UserDetail() {
  const { id } = useParams<{ id: string }>();
  const [u, setU] = useState<AdminUserDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    adminConsole
      .user(id)
      .then((r) => setU(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!u) return <LoadingState />;
  return (
    <>
      <PageHeader
        title={u.full_name}
        description="用户资料与售后活动只读摘要"
      />
      <SectionCard title="基础资料">
        <dl className="grid gap-4 p-5 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-slate-500">邮箱</dt>
            <dd>{u.email}</dd>
          </div>
          <div>
            <dt className="text-slate-500">角色</dt>
            <dd>{labelFor(u.role)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">风险等级</dt>
            <dd>
              <StatusBadge value={u.risk_level} />
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">注册时间</dt>
            <dd>{formatDateTime(u.created_at)}</dd>
          </div>
        </dl>
      </SectionCard>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        {[
          ["最近订单", u.orders, "order_number", "status"],
          ["最近工单", u.tickets, "ticket_number", "status"],
          ["Memory 摘要", u.memories, "content", "status"],
          ["最近 Agent 会话", u.sessions, "id", "status"],
        ].map(([title, rows, main, status]) => (
          <SectionCard key={String(title)} title={String(title)}>
            <div className="divide-y">
              {(rows as Record<string, unknown>[]).length ? (
                (rows as Record<string, unknown>[]).map((row, index) => (
                  <div
                    key={String(row.id || index)}
                    className="flex justify-between gap-3 p-4 text-sm"
                  >
                    <span className="truncate">
                      {String(row[String(main)] || "—")}
                    </span>
                    <StatusBadge value={String(row[String(status)] || "")} />
                  </div>
                ))
              ) : (
                <p className="p-5 text-sm text-slate-500">暂无数据</p>
              )}
            </div>
          </SectionCard>
        ))}
      </div>
    </>
  );
}
