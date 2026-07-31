export const STATUS_LABELS: Record<string, string> = {
  PENDING: "待处理",
  PENDING_APPROVAL: "待审批",
  APPROVED: "已批准",
  REJECTED: "已拒绝",
  COMPLETED: "已完成",
  FAILED: "执行失败",
  CANCELLED: "已取消",
  SHIPPED: "已发货",
  DELIVERED: "已签收",
  PAID: "已付款",
  PENDING_PAYMENT: "待付款",
  IN_TRANSIT: "运输中",
  OUT_FOR_DELIVERY: "派送中",
  PICKED_UP: "已揽收",
  RETURNED: "已退回",
  REFUNDED: "已退款",
  ACTIVE: "生效中",
  DRAFT: "草稿",
  ARCHIVED: "已归档",
  SUPERSEDED: "已被新版替代",
  NEEDS_REVIEW: "待审核",
  EXPIRED: "已过期",
};
export const TYPE_LABELS: Record<string, string> = {
  REFUND: "退款",
  RETURN: "退货",
  EXCHANGE: "换货",
  REPLACEMENT: "补发",
  RESHIPMENT: "补发",
  QUALITY_REFUND: "质量问题退款",
  PRE_SHIP_REFUND: "发货前退款",
  MISSING_PARTS: "少件补发",
  HIGH: "高风险",
  CRITICAL: "严重风险",
  MEDIUM: "中风险",
  LOW: "低风险",
  ADMIN: "管理员",
  OPERATOR: "运营人员",
  CUSTOMER: "顾客",
  GENERAL: "平台规则",
  SOP: "运营流程",
  RISK: "风险控制",
  LOGISTICS: "物流争议",
};
export const TOOL_LABELS: Record<string, string> = {
  search_after_sales_policy: "售后政策检索",
  create_after_sales_ticket: "创建售后工单",
  get_order_status: "查询订单状态",
  create_refund: "创建退款",
  create_reshipment: "创建补发",
};
export const NODE_LABELS: Record<string, string> = {
  load_context: "加载上下文",
  classify_intent: "识别用户意图",
  retrieve_memory: "检索记忆",
  select_tools: "选择处理工具",
  authorize_tool: "校验工具权限",
  execute_tool: "执行工具",
  validate_result: "验证结果",
  compose_response: "生成回复",
  persist_observe: "持久化与观测",
  handle_tool_error: "处理工具异常",
};
export const labelFor = (value?: string | null) =>
  value
    ? STATUS_LABELS[value] ||
      TYPE_LABELS[value] ||
      TOOL_LABELS[value] ||
      NODE_LABELS[value] ||
      value
    : "—";
export const formatCurrency = (v: string | number) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY" }).format(
    Number(v),
  );
export const formatNumber = (v: number) =>
  new Intl.NumberFormat("zh-CN").format(v);
export const formatDateTime = (v?: string | null) =>
  v
    ? new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
        .format(new Date(v))
        .replaceAll("/", "-")
    : "—";
export const formatDuration = (ms: number) =>
  ms >= 1000 ? `${(ms / 1000).toFixed(1)} 秒` : `${ms} 毫秒`;
export function friendlyError(error: unknown) {
  const m = error instanceof Error ? error.message : "";
  if (/401|Authentication required/i.test(m))
    return "登录状态已过期，请重新登录";
  if (/403|permission|forbidden/i.test(m)) return "当前账号无权限执行此操作";
  if (/404|not found/i.test(m)) return "未找到对应数据";
  if (/ACTION_ALREADY_CONSUMED|CONFLICT|409/i.test(m))
    return "该操作已处理，请勿重复提交";
  if (/422|validation/i.test(m)) return "提交内容不完整或格式不正确";
  if (/network|fetch/i.test(m)) return "网络连接失败，请检查服务状态";
  return m && !/Error \d+|Request failed|Internal Server Error/i.test(m)
    ? m
    : "系统暂时无法处理，请稍后重试";
}
