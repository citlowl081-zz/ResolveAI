"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminPolicies, type Policy } from "@/lib/api";
import { formatDateTime, friendlyError, labelFor } from "@/lib/labels";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/admin-ui";
export default function PolicyDetail() {
  const { key } = useParams<{ key: string }>();
  const [p, setP] = useState<Policy | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    adminPolicies
      .getByKey(decodeURIComponent(key))
      .then((r) => setP(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, [key]);
  if (error) return <ErrorState message={error} />;
  if (!p) return <LoadingState />;
  return (
    <>
      <PageHeader
        title={p.title}
        description={`${p.policy_key} · 版本 ${p.version}`}
      />
      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard title="政策属性" className="xl:col-span-1">
          <dl className="space-y-4 p-5 text-sm">
            <div>
              <dt className="text-slate-500">状态</dt>
              <dd>
                <StatusBadge value={p.status} />
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">规则类别</dt>
              <dd>{labelFor(p.category)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">生效日期</dt>
              <dd>{formatDateTime(p.effective_date)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">来源</dt>
              <dd>{p.source || "未标注"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">知识片段</dt>
              <dd>由入库流程生成，当前详情接口未返回数量</dd>
            </div>
          </dl>
        </SectionCard>
        <SectionCard title="政策正文" className="xl:col-span-2">
          <article className="whitespace-pre-wrap p-5 text-sm leading-7">
            {p.content || p.content_summary || "暂无正文"}
          </article>
        </SectionCard>
      </div>
      <SectionCard title="引用预览与适用范围" className="mt-5">
        <p className="p-5 text-sm text-slate-500">
          检索时使用真实生效版本的 Policy
          Key、标题和版本作为结构化引用；内部运营规则不作为法律强制要求展示。
        </p>
      </SectionCard>
    </>
  );
}
