"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminTraces, type AgentTrace } from "@/lib/api";
import {
  formatDuration,
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
const expected = [
  "load_context",
  "classify_intent",
  "retrieve_memory",
  "select_tools",
  "authorize_tool",
  "execute_tool",
  "validate_result",
  "compose_response",
  "persist_observe",
];
export default function TraceDetail() {
  const { id } = useParams<{ id: string }>();
  const [nodes, setNodes] = useState<AgentTrace[] | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    adminTraces
      .get(id)
      .then((r) => setNodes(r.data.nodes))
      .catch((e) => setError(friendlyError(e)));
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!nodes) return <LoadingState />;
  return (
    <>
      <PageHeader title="Agent 追踪详情" description={`Trace ID：${id}`} />
      <SectionCard title="9 节点执行时间线">
        <ol className="p-5">
          {expected.map((name, index) => {
            const n = nodes.find((x) => x.node_name === name) || nodes[index];
            return (
              <li
                key={name}
                className="relative border-l-2 border-slate-200 pb-6 pl-6 last:pb-0"
              >
                <span className="absolute -left-2 top-0 grid h-4 w-4 place-items-center rounded-full bg-blue-500 text-[9px] text-white">
                  {index + 1}
                </span>
                <div className="flex flex-wrap items-center gap-3">
                  <strong>{n ? labelFor(n.node_name) : labelFor(name)}</strong>
                  <StatusBadge
                    value={n?.is_success ? "COMPLETED" : "PENDING"}
                  />
                  <span className="text-xs text-slate-500">
                    {n ? formatDuration(n.duration_ms) : "暂无记录"}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  技术标识：{n?.node_name || name} · 时间：
                  {formatDateTime(n?.created_at)}
                </p>
                {n?.error_code && (
                  <p className="mt-1 text-sm text-red-600">
                    错误类型：{n.error_code}
                  </p>
                )}
              </li>
            );
          })}
        </ol>
      </SectionCard>
    </>
  );
}
