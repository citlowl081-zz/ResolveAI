"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminToolLogs, type ToolLog } from "@/lib/api";
import {
  formatDateTime,
  formatDuration,
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
export default function ToolLogDetail() {
  const { id } = useParams<{ id: string }>();
  const [log, setLog] = useState<ToolLog | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    adminToolLogs
      .get(id)
      .then((r) => setLog(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!log) return <LoadingState />;
  return (
    <>
      <PageHeader title="工具日志详情" description={`日志编号 ${log.id}`} />
      <SectionCard>
        <dl className="grid gap-5 p-5 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-slate-500">工具名称</dt>
            <dd>
              {labelFor(log.tool_name)}
              <small className="block text-slate-400">
                技术标识：{log.tool_name}
              </small>
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">执行状态</dt>
            <dd>
              <StatusBadge value={log.is_success ? "COMPLETED" : "FAILED"} />
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">耗时</dt>
            <dd>{formatDuration(log.duration_ms)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">重试次数</dt>
            <dd>{log.retry_count || 0}</dd>
          </div>
          <div>
            <dt className="text-slate-500">错误类型</dt>
            <dd>{log.error_code || "无"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">创建时间</dt>
            <dd>{formatDateTime(log.created_at)}</dd>
          </div>
        </dl>
        <p className="border-t p-5 text-sm text-slate-500">
          工具参数、完整执行结果与幂等 Key
          不在管理端接口中返回，避免泄露敏感信息。
        </p>
      </SectionCard>
    </>
  );
}
