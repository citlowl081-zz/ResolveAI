"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminConsole, type AdminOrderDetail } from "@/lib/api";
import {
  formatCurrency,
  formatDateTime,
  friendlyError,
  labelFor,
} from "@/lib/labels";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/admin-ui";
export default function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const [o, setO] = useState<AdminOrderDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    adminConsole
      .order(id)
      .then((r) => setO(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!o) return <LoadingState />;
  return (
    <>
      <PageHeader
        title={`订单 ${o.order_number}`}
        description="订单、商品、物流与关联售后信息"
      />
      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="订单基础信息">
          <dl className="grid grid-cols-2 gap-4 p-5 text-sm">
            <div>
              <dt className="text-slate-500">用户</dt>
              <dd>{o.user_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">状态</dt>
              <dd>
                <StatusBadge value={o.status} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">实付金额</dt>
              <dd>{formatCurrency(o.paid_amount)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">创建时间</dt>
              <dd>{formatDateTime(o.created_at)}</dd>
            </div>
          </dl>
        </SectionCard>
        <SectionCard title="物流信息">
          <div className="p-5 text-sm">
            {o.logistics ? (
              <div className="space-y-2">
                <p>状态：{labelFor(o.logistics.status)}</p>
                <p>承运商：{o.logistics.carrier}</p>
                <p>运单号：{o.logistics.tracking_number}</p>
                <p>当前位置：{o.logistics.current_location || "暂无更新"}</p>
              </div>
            ) : (
              <p className="text-slate-500">暂无物流记录</p>
            )}
          </div>
        </SectionCard>
      </div>
      <SectionCard title="商品明细" className="mt-5">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="p-3 text-left">商品</th>
                <th>单价</th>
                <th>数量</th>
                <th>小计</th>
              </tr>
            </thead>
            <tbody>
              {o.items.map((i) => (
                <tr key={i.id} className="border-t">
                  <td className="p-3">{i.product_name}</td>
                  <td className="text-center">
                    {formatCurrency(i.unit_price)}
                  </td>
                  <td className="text-center">{i.quantity}</td>
                  <td className="text-center">{formatCurrency(i.subtotal)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
      <SectionCard title="关联售后工单" className="mt-5">
        <div className="divide-y">
          {o.tickets.length ? (
            o.tickets.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between p-4 text-sm"
              >
                <span>
                  {t.ticket_number} · {labelFor(t.intent)}
                </span>
                <StatusBadge value={t.status} />
              </div>
            ))
          ) : (
            <p className="p-5 text-sm text-slate-500">暂无关联工单</p>
          )}
        </div>
      </SectionCard>
    </>
  );
}
