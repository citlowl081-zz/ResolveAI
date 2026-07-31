"use client";
import { useEffect, useState } from "react";
import { adminConsole, type SystemStatus } from "@/lib/api";
import { formatDateTime, friendlyError } from "@/lib/labels";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/admin-ui";
export default function SystemPage() {
  const [data, setData] = useState<SystemStatus | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    adminConsole
      .system()
      .then((r) => setData(r.data))
      .catch((e) => setError(friendlyError(e)));
  }, []);
  return (
    <>
      <PageHeader
        title="系统状态"
        description="仅展示运行状态和配置是否存在，不展示任何密钥或服务地址"
      />
      {error ? (
        <ErrorState message={error} />
      ) : !data ? (
        <LoadingState />
      ) : (
        <SectionCard>
          <dl className="grid gap-0 sm:grid-cols-2 xl:grid-cols-3">
            {[
              ["后端服务", data.backend === "healthy" ? "正常" : "异常"],
              ["数据库", data.database === "healthy" ? "正常" : "异常"],
              [
                "大模型服务商",
                data.provider === "mock" ? "Mock" : "千问（OpenAI 兼容）",
              ],
              ["当前模型", data.model],
              [
                "向量模型服务",
                data.embedding_provider === "mock"
                  ? "Mock"
                  : data.embedding_provider,
              ],
              ["知识库生效政策", String(data.active_policy_count)],
              ["接口密钥", data.api_key_configured ? "已配置" : "未配置"],
              ["服务地址", data.base_url_configured ? "已配置" : "未配置"],
              ["最近政策更新", formatDateTime(data.latest_policy_update)],
              [
                "最近一次 Seed",
                data.latest_seed ? formatDateTime(data.latest_seed) : "当前版本未记录",
              ],
              ["最近工具失败", formatDateTime(data.latest_tool_failure)],
              ["应用版本", data.app_version],
            ].map(([k, v]) => (
              <div key={k} className="border-b p-5">
                <dt className="text-sm text-slate-500">{k}</dt>
                <dd className="mt-2 font-medium">
                  {/后端|数据库/.test(k) ? (
                    <StatusBadge value={v === "正常" ? "ACTIVE" : "FAILED"} />
                  ) : (
                    v
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </SectionCard>
      )}
    </>
  );
}
