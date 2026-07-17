---
policy_key: POL-SOP-901
title: 无政策结果时的人工升级规则
category: SOP
effective_date: 2025-01-01
issue_types:
  - 政策缺失
  - 人工升级
  - 未知场景
content_summary: 当 AI Agent 无法从知识库中检索到匹配的政策时（检索结果为空或相似度低于阈值），系统应将请求标记为需要人工处理，并转交给人工客服。不得在无政策依据的情况下给出建议。
source:
  document: ResolveAI 内部运营规则
  issuing_authority: ResolveAI Platform
  url: 无（内部规则）
  accessed: 2026-07-16
  note: 内部运营规则，非法律规定
metadata_filter:
  rule_type: internal
---

# 无政策结果时的人工升级规则

## 触发条件
1. RAG 检索结果为空（无任何匹配的政策文档）；
2. 所有检索结果相似度均低于 0.3（平台默认最低阈值）；
3. 用户明确要求转人工服务的；
4. AI Agent 在连续两轮对话中无法确定用户意图的。

## 升级流程
1. AI Agent 在回复中告知用户将转接人工客服；
2. 系统自动创建转人工工单，标注升级原因；
3. 人工客服接管会话并查看对话历史；
4. 人工客服在处理完毕后可补充或新建政策文档。

## 禁止行为
1. AI Agent 不得在无政策依据的情况下编造或推测政策内容；
2. AI Agent 不得在检索为空时声称有相关政策；
3. citations 为空时不展示政策引用。

## 重要声明
> 本规则为 ResolveAI 平台内部运营规则。政策检索阈值的具体数值可在系统配置中调整。
