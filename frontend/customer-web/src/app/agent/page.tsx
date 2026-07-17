"use client";
import { useState, useEffect, useRef } from "react";
import Navbar from "@/lib/navbar";
import { agent, type ProposedAction, type Citation, type ApprovalTask, type AgentResponse } from "@/lib/api";

function uuid() { return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`; }

interface Message { role: "user" | "assistant" | "system"; content: string; citations?: Citation[]; action?: ProposedAction | null; approval?: { approval_type?: string; status?: string; reason?: string } | null; }

export default function AgentPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [pendingAction, setPendingAction] = useState<ProposedAction | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function send(msg: string, confirmActionId: string | null = null) {
    setSending(true);
    try {
      const idemKey = uuid();
      let res: { success?: boolean; data?: AgentResponse; code?: string; message?: string };
      if (!sessionId) {
        res = await agent.createSessionRaw(msg, idemKey);
        if (res.data?.session_id) setSessionId(res.data.session_id);
      } else {
        res = await agent.sendMessage(sessionId, msg, confirmActionId, idemKey);
      }
      const d = (res as { data?: AgentResponse }).data || (res as unknown as AgentResponse);
      const citations = d.citations || [];
      const actions = d.proposed_actions || [];
      const action = actions.length > 0 ? actions[0] : null;
      const approval = d.approval || null;

      setMessages(prev => [
        ...prev,
        { role: "user", content: msg },
        {
          role: "assistant",
          content: d.message || getResponseText(d),
          citations,
          action,
          approval,
        },
      ]);
      if (action && action.status === "pending_confirmation") {
        setPendingAction(action);
      } else {
        setPendingAction(null);
      }
      if (d.session_id && !sessionId) setSessionId(d.session_id);
    } catch (e: unknown) {
      setMessages(prev => [...prev, { role: "system", content: `错误: ${e instanceof Error ? e.message : "请求失败"}` }]);
    } finally {
      setSending(false);
    }
  }

  function getResponseText(d: AgentResponse): string {
    if (d.status === "PENDING_APPROVAL") return d.message || "您的高风险操作需要人工审核，请耐心等待。";
    if (d.proposed_actions?.length) return `${d.message || "请确认以下操作："}\n${d.proposed_actions[0].description}`;
    return d.message || "请问还有什么可以帮您的？";
  }

  function handleConfirm() {
    if (!pendingAction) return;
    send(`确认执行 ${pendingAction.description}`, pendingAction.action_id);
  }

  function handleDecline() {
    setPendingAction(null);
    setMessages(prev => [...prev, { role: "system", content: "已取消操作。" }]);
  }

  return (
    <div className="flex flex-col h-screen">
      <Navbar />
      <div className="flex-1 overflow-y-auto p-4 max-w-3xl mx-auto w-full">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <p className="text-lg">👋 欢迎使用 ResolveAI 智能客服</p>
            <p className="text-sm mt-2">您可以询问订单、物流、退款和售后问题</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`mb-4 ${m.role === "user" ? "text-right" : "text-left"}`}>
            <div className={`inline-block max-w-[80%] p-3 rounded-xl text-sm ${
              m.role === "user" ? "bg-blue-600 text-white" :
              m.role === "system" ? "bg-red-50 text-red-600" : "bg-white border"
            }`}>
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.citations && m.citations.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <p className="text-xs font-semibold text-gray-500 mb-1">📋 政策引用:</p>
                  {m.citations.map((c, j) => (
                    <div key={j} className="text-xs text-gray-500 mt-1">
                      <span className="font-mono bg-gray-100 px-1 rounded">{c.policy_key}</span> v{c.version} — {c.title} ({(c.similarity_score * 100).toFixed(0)}%)
                      {c.source && <span> · {c.source === "legal_requirement" ? "法律规则" : "平台规则"}</span>}
                    </div>
                  ))}
                </div>
              )}
              {m.action && (
                <div className="mt-2 p-2 bg-blue-50 rounded text-xs">
                  <p className="font-semibold">📌 待确认操作: {m.action.description}</p>
                  <p className="text-gray-400">状态: {m.action.status}</p>
                </div>
              )}
              {m.approval && (
                <div className="mt-2 p-2 bg-yellow-50 rounded text-xs">
                  <p className="font-semibold text-yellow-700">⏳ 等待人工审批</p>
                  <p className="text-yellow-600">类型: {m.approval.approval_type} | 状态: {m.approval.status}</p>
                </div>
              )}
            </div>
          </div>
        ))}
        {pendingAction && (
          <div className="flex gap-3 justify-center mb-4">
            <button onClick={handleConfirm} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">确认执行</button>
            <button onClick={handleDecline} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">取消</button>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t bg-white p-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !sending) { send(input); setInput(""); } }}
            placeholder="输入您的问题..." disabled={sending}
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onClick={() => { send(input); setInput(""); }} disabled={sending || !input.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">{sending ? "..." : "发送"}</button>
        </div>
      </div>
    </div>
  );
}
