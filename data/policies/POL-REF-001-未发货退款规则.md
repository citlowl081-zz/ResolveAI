---
policy_key: POL-REF-001
title: 未发货退款规则
category: REFUND
effective_date: 2024-01-01
issue_types:
  - PRE_SHIP_REFUND
source: company_policy
metadata_filter:
  max_days_from_payment: null
  allowed_order_statuses: ["PENDING_PAYMENT", "PAID"]
  allowed_refund_types: ["FULL"]
  requires_return_shipping: false
  requires_original_packaging: false
---
# 未发货退款规则

## 适用范围
订单状态为"待付款"或"已付款"但尚未发货的订单，客户可申请全额退款。

## 退款规则
1. 全额退款包括商品金额和已支付的运费。
2. 退款将在1-3个工作日内原路返回客户的支付账户。
3. 使用优惠券的订单，优惠券金额不予退还，仅退还实际支付金额。

## 退款流程
1. 客户在订单详情页点击"申请退款"。
2. 系统自动审核订单状态为未发货。
3. 审核通过后自动执行退款，无需人工介入。
