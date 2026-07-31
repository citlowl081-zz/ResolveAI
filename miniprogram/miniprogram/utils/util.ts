export function uuid(): string {
  const s = () => (((1 + Math.random()) * 0x10000) | 0).toString(16).substring(1);
  return s() + s() + "-" + s() + "-" + s() + "-" + s() + "-" + s() + s() + s();
}

export const STATUS_MAP: Record<string, string> = {
  PENDING_PAYMENT: "待支付", PAID: "已支付", SHIPPED: "已发货",
  DELIVERED: "已签收", CANCELLED: "已取消", REFUNDED: "已退款",
  APPROVED: "已通过", REJECTED: "已拒绝", COMPLETED: "已完成",
  NEEDS_REVIEW: "待审核", PENDING: "待审批", ACTIVE: "生效中",
  DRAFT: "草稿", SUPERSEDED: "已替代", ARCHIVED: "已归档",
  EXPIRED: "已过期",
  PROCESSING: "处理中", FAILED: "失败", CANCELLED: "已取消",
  CREATED: "已创建", PICKED_UP: "已揽收", IN_TRANSIT: "运输中",
  OUT_FOR_DELIVERY: "派送中", DELIVERY_FAILED: "派送失败",
};

export const LABEL_MAP: Record<string, string> = {
  PREFERENCE: "偏好", FACT: "事实", SUMMARY: "摘要", COMMITMENT: "承诺",
  RISK_PROFILE: "风险偏好", LOW: "低", MEDIUM: "中", HIGH: "高",
  CRITICAL: "严重", CREATE_AFTER_SALES_TICKET: "创建售后工单",
  create_after_sales_ticket: "创建售后工单", create_refund: "创建退款",
  create_reshipment: "创建补发", PRE_SHIP_REFUND: "发货前退款",
  POST_SHIP_REFUND: "发货后退款", RETURN_REFUND: "退货退款",
  EXCHANGE: "换货", RESHIP: "补发",
  HIGH_REFUND: "高额退款", RISK_HIT: "风险规则命中", MULTI_ITEM: "多件商品",
  MANUAL_REQUEST: "人工审批请求", REFUND: "退款", RETURN: "退货",
  LOGISTICS: "物流问题", QUALITY_ISSUE: "质量问题",
};

export function fmtDate(s?: string): string {
  if (!s) return "-";
  try { return new Date(s).toLocaleString("zh-CN"); } catch { return s; }
}
