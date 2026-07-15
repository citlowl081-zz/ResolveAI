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
};

export function fmtDate(s?: string): string {
  if (!s) return "-";
  try { return new Date(s).toLocaleString("zh-CN"); } catch { return s; }
}
