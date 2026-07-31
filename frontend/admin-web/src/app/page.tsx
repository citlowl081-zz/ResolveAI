"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { adminConsole, type DashboardMetrics } from "@/lib/api";
import { friendlyError, labelFor } from "@/lib/labels";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatCard,
  StatusBadge,
} from "@/components/admin-ui";

export default function DashboardPage() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<DashboardMetrics | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    setData(null);
    adminConsole
      .dashboard(days)
      .then((r) => setData(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, [days]);
  useEffect(load, [load]);
  return (
    <>
      <PageHeader
        title="数据看板"
        description="基于当前数据库的售后运营与 Agent 运行指标"
        action={
          <select
            aria-label="统计时间范围"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-md border bg-white px-3 py-2 text-sm"
          >
            <option value={7}>近 7 天</option>
            <option value={30}>近 30 天</option>
          </select>
        }
      />
      {error ? (
        <ErrorState message={error} retry={load} />
      ) : !data ? (
        <LoadingState />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[
              ["待处理工单", data.pending_tickets],
              ["今日新增工单", data.today_tickets],
              ["待审批操作", data.pending_approvals],
              ["Agent 会话", data.agent_sessions],
              ["政策检索次数", data.policy_searches],
              ["最近失败调用", data.failed_tool_calls],
            ].map(([label, value]) => (
              <StatCard
                key={label}
                label={String(label)}
                value={value}
                hint={label === "Agent 会话" ? `近 ${days} 天` : undefined}
              />
            ))}
          </div>
          <div className="mt-6 grid gap-5 xl:grid-cols-2">
            <SectionCard title={`近 ${days} 日工单趋势`}>
              <div className="p-5">
                {data.ticket_trend.length ? (
                  <div className="flex h-40 items-end gap-2">
                    {data.ticket_trend.map((x) => (
                      <div
                        key={x.date}
                        className="flex min-w-0 flex-1 flex-col items-center gap-2"
                      >
                        <span className="text-xs">{x.count}</span>
                        <div
                          className="w-full rounded-t bg-blue-500"
                          style={{ height: `${Math.max(8, x.count * 18)}px` }}
                        />
                        <span className="truncate text-[10px] text-slate-400">
                          {x.date.slice(5)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState />
                )}
              </div>
            </SectionCard>
            <SectionCard title="工单状态分布">
              <div className="space-y-3 p-5">
                {data.ticket_statuses.length ? (
                  data.ticket_statuses.map((x) => (
                    <div
                      key={x.status}
                      className="flex items-center justify-between"
                    >
                      <StatusBadge value={x.status} />
                      <strong>{x.count}</strong>
                    </div>
                  ))
                ) : (
                  <EmptyState />
                )}
              </div>
            </SectionCard>
          </div>
          <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <SectionCard title="最近高风险审批">
              <div className="divide-y">
                {data.recent_high_risk_approvals.length ? (
                  data.recent_high_risk_approvals.map((x) => (
                    <Link
                      key={x.id}
                      href={`/approvals/${x.id}`}
                      className="flex justify-between p-4 text-sm hover:bg-slate-50"
                    >
                      <span>{labelFor(x.tool_name)}</span>
                      <StatusBadge value={x.status} />
                    </Link>
                  ))
                ) : (
                  <EmptyState />
                )}
              </div>
            </SectionCard>
            <SectionCard title="最近工具执行失败">
              <div className="divide-y">
                {data.recent_failed_tools.length ? (
                  data.recent_failed_tools.map((x) => (
                    <Link
                      key={String(x.id)}
                      href={`/tool-logs/${x.id}`}
                      className="flex justify-between p-4 text-sm hover:bg-slate-50"
                    >
                      <span>{labelFor(String(x.tool_name))}</span>
                      <span className="text-red-600">
                        {String(x.error_code || "执行失败")}
                      </span>
                    </Link>
                  ))
                ) : (
                  <EmptyState />
                )}
              </div>
            </SectionCard>
          </div>
        </>
      )}
    </>
  );
}
