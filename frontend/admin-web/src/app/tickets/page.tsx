"use client";
import { useEffect, useState } from "react";
import { adminTickets, type Ticket } from "@/lib/api";
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
export default function TicketsPage() {
  const [items, setItems] = useState<Ticket[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1);
  const [status, setStatus] = useState(""),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  useEffect(() => {
    setLoading(true);
    adminTickets
      .list(page, status || undefined)
      .then((r) => {
        setItems(r.data.items);
        setTotal(r.data.total);
        setError("");
      })
      .catch((e) => setError(friendlyError(e)))
      .finally(() => setLoading(false));
  }, [page, status]);
  return (
    <>
      <PageHeader title="工单管理" description="售后工单、风险状态与处理进度" />
      <div className="mb-4 flex flex-wrap gap-2">
        {[
          "",
          "NEEDS_REVIEW",
          "APPROVED",
          "COMPLETED",
          "REJECTED",
          "CANCELLED",
        ].map((s) => (
          <button
            key={s}
            onClick={() => {
              setStatus(s);
              setPage(1);
            }}
            className={`rounded-md border px-3 py-2 text-sm ${status === s ? "border-blue-600 bg-blue-600 text-white" : "bg-white"}`}
          >
            {s ? labelFor(s) : "全部状态"}
          </button>
        ))}
      </div>
      {error ? (
        <ErrorState message={error} />
      ) : (
        <SectionCard>
          {loading ? (
            <LoadingState />
          ) : items.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    {[
                      "工单编号",
                      "订单",
                      "售后类型",
                      "状态",
                      "创建时间",
                      "更新时间",
                      "操作",
                    ].map((x) => (
                      <th key={x} className="p-3">
                        {x}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {items.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50">
                      <td className="p-3 font-mono text-xs">
                        {t.ticket_number}
                      </td>
                      <td className="p-3 font-mono text-xs">
                        {t.order_id.slice(0, 8)}…
                      </td>
                      <td className="p-3">{labelFor(t.intent)}</td>
                      <td className="p-3">
                        <StatusBadge value={t.status} />
                      </td>
                      <td className="p-3">{formatDateTime(t.created_at)}</td>
                      <td className="p-3">{formatDateTime(t.updated_at)}</td>
                      <td className="p-3">
                        <DetailLink href={`/tickets/${t.id}`} />
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
