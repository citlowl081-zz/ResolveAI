"use client";
import { useCallback, useEffect, useState } from "react";
import { adminConsole, type AdminOrder } from "@/lib/api";
import { formatCurrency, formatDateTime, friendlyError } from "@/lib/labels";
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
export default function OrdersPage() {
  const [items, setItems] = useState<AdminOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setLoading(true);
    setError("");
    adminConsole
      .orders(page, query, status)
      .then((r) => {
        setItems(r.data.items);
        setTotal(r.data.total);
      })
      .catch((e) => setError(friendlyError(e)))
      .finally(() => setLoading(false));
  }, [page, query, status]);
  useEffect(load, [load]);
  return (
    <>
      <PageHeader
        title="订单管理"
        description="只读查看订单、物流与关联售后记录"
      />
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          aria-label="搜索订单"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
          placeholder="订单号或用户姓名"
          className="rounded-md border px-3 py-2 text-sm"
        />
        <select
          aria-label="订单状态"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className="rounded-md border px-3 py-2 text-sm"
        >
          <option value="">全部状态</option>
          <option value="PAID">已付款</option>
          <option value="SHIPPED">已发货</option>
          <option value="DELIVERED">已签收</option>
          <option value="REFUNDED">已退款</option>
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
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-slate-600">
                  <tr>
                    {[
                      "订单号",
                      "用户",
                      "商品摘要",
                      "金额",
                      "状态",
                      "物流状态",
                      "售后工单",
                      "创建时间",
                      "操作",
                    ].map((x) => (
                      <th key={x} className="px-4 py-3">
                        {x}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {items.map((o) => (
                    <tr key={o.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-xs">
                        {o.order_number}
                      </td>
                      <td className="px-4 py-3">{o.user_name}</td>
                      <td className="max-w-56 truncate px-4 py-3">
                        {o.item_summary || "—"}
                      </td>
                      <td className="px-4 py-3">
                        {formatCurrency(o.paid_amount)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge value={o.status} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge value={o.logistics_status} />
                      </td>
                      <td className="px-4 py-3">{o.ticket_count}</td>
                      <td className="px-4 py-3">
                        {formatDateTime(o.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <DetailLink href={`/orders/${o.id}`} />
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
