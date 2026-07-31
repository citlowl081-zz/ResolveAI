"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminTickets, type Ticket } from "@/lib/api";
import { formatDateTime, friendlyError, labelFor } from "@/lib/labels";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/admin-ui";
export default function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const [ticket, setTicket] = useState<Ticket | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    adminTickets
      .get(id)
      .then((r) => setTicket(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!ticket) return <LoadingState />;
  return (
    <>
      <PageHeader
        title={`工单 ${ticket.ticket_number}`}
        description="工单基本信息与安全处理状态"
      />
      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard title="基本信息">
          <dl className="grid grid-cols-2 gap-4 p-5 text-sm">
            <div>
              <dt className="text-slate-500">状态</dt>
              <dd>
                <StatusBadge value={ticket.status} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">售后类型</dt>
              <dd>{labelFor(ticket.intent)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">订单 ID</dt>
              <dd className="break-all font-mono text-xs">{ticket.order_id}</dd>
            </div>
            <div>
              <dt className="text-slate-500">版本</dt>
              <dd>v{ticket.version}</dd>
            </div>
            <div>
              <dt className="text-slate-500">创建时间</dt>
              <dd>{formatDateTime(ticket.created_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">更新时间</dt>
              <dd>{formatDateTime(ticket.updated_at)}</dd>
            </div>
          </dl>
        </SectionCard>
        <SectionCard title="处理说明">
          <div className="space-y-3 p-5 text-sm">
            <p>
              <span className="text-slate-500">用户诉求：</span>
              {ticket.customer_request || "暂无记录"}
            </p>
            <p>
              <span className="text-slate-500">运营备注：</span>
              {ticket.operator_notes || "暂无记录"}
            </p>
            {ticket.reject_reason && (
              <p className="text-red-700">拒绝原因：{ticket.reject_reason}</p>
            )}
          </div>
        </SectionCard>
      </div>
      <SectionCard title="关联信息" className="mt-5">
        <p className="p-5 text-sm text-slate-500">
          Agent
          会话、工具日志、审批与政策引用可分别在追踪、日志和审批页面按关联标识查询。当前详情接口未返回的数据不会在页面中伪造。
        </p>
      </SectionCard>
    </>
  );
}
