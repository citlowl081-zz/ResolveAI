"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminApprovals, type ApprovalTask } from "@/lib/api";
import { formatDateTime, friendlyError, labelFor } from "@/lib/labels";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/admin-ui";
export default function ApprovalDetail() {
  const { id } = useParams<{ id: string }>();
  const [a, setA] = useState<ApprovalTask | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    adminApprovals
      .get(id)
      .then((r) => setA(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!a) return <LoadingState />;
  return (
    <>
      <PageHeader title="审批详情" description={`审批编号 ${a.id}`} />
      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard title="审批信息">
          <dl className="space-y-4 p-5 text-sm">
            <div>
              <dt className="text-slate-500">状态</dt>
              <dd>
                <StatusBadge value={a.status} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">风险等级</dt>
              <dd>
                <StatusBadge value={a.risk_level} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">操作类型</dt>
              <dd>
                {labelFor(a.tool_name)}
                <small className="ml-2 text-slate-400">
                  技术标识：{a.tool_name}
                </small>
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">创建时间</dt>
              <dd>{formatDateTime(a.created_at)}</dd>
            </div>
          </dl>
        </SectionCard>
        <SectionCard title="风险与决策">
          <div className="space-y-3 p-5 text-sm">
            <p>风险原因：{a.reason || "未记录"}</p>
            <p>决策理由：{a.decision_reason || "尚未决策"}</p>
            <p>
              执行参数：仅在后端保留脱敏摘要，当前接口不向页面返回敏感字段。
            </p>
          </div>
        </SectionCard>
      </div>
    </>
  );
}
