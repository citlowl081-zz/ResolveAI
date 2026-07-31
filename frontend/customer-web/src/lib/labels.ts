export const STATUS_LABELS: Record<string, string> = {
  PENDING: "待处理", PENDING_APPROVAL: "待审批", APPROVED: "已批准",
  REJECTED: "已拒绝", COMPLETED: "已完成", FAILED: "执行失败",
  CANCELLED: "已取消", PAID: "已支付", SHIPPED: "已发货",
  DELIVERED: "已签收", REFUNDED: "已退款", ACTIVE: "生效中",
  DRAFT: "草稿", ARCHIVED: "已归档", NEEDS_REVIEW: "待审核", IN_TRANSIT: "运输中", OUT_FOR_DELIVERY: "派送中",
};

export const TYPE_LABELS: Record<string, string> = {
  REFUND: "退款", RETURN: "退货", EXCHANGE: "换货", REPLACEMENT: "补发",
  RESHIPMENT: "补发", QUALITY_REFUND: "质量问题退款", PRE_SHIP_REFUND: "发货前退款",
  MISSING_PARTS: "少件补发", LOGISTICS_INQUIRY: "物流查询",
  HIGH: "高风险", MEDIUM: "中风险", LOW: "低风险",
  GENERAL: "平台规则", SOP: "运营流程", RISK: "风险控制", LOGISTICS: "物流争议",
};

export const TOOL_LABELS: Record<string, string> = {
  search_after_sales_policy: "售后政策检索",
  create_after_sales_ticket: "创建售后工单",
  get_order_status: "查询订单状态",
};

export function labelFor(value?: string | null): string {
  if (!value) return "—";
  return STATUS_LABELS[value] || TYPE_LABELS[value] || TOOL_LABELS[value] || value;
}

export const formatCurrency = (value: string | number) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY" }).format(Number(value));
export const formatNumber = (value: number) => new Intl.NumberFormat("zh-CN").format(value);
export const formatDateTime = (value?: string | null) => value
  ? new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value)).replaceAll("/", "-")
  : "—";

export function friendlyError(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (/401|Authentication required/i.test(message)) return "登录状态已过期，请重新登录";
  if (/403|permission|forbidden/i.test(message)) return "当前账号无权限执行此操作";
  if (/404|not found/i.test(message)) return "未找到对应数据";
  if (/ACTION_ALREADY_CONSUMED|CONFLICT|409/i.test(message)) return "该操作已处理，请勿重复提交";
  if (/422|validation/i.test(message)) return "提交内容不完整或格式不正确";
  if (/network|fetch/i.test(message)) return "网络连接失败，请检查服务状态";
  return message && !/Request failed|Error \d+|Internal Server Error/i.test(message) ? message : "系统暂时无法处理，请稍后重试";
}
