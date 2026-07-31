"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import Navbar from "@/lib/navbar";
import {
  agent,
  memories,
  type AgentMessage,
  type AgentResponse,
  type AgentSession,
  type ApprovalTask,
  type ProposedAction,
} from "@/lib/api";
import { friendlyError, labelFor } from "@/lib/labels";

const LAST_SESSION_KEY = "resolveai:last_agent_session";

type ChatMessage = AgentMessage & {
  approval?: Partial<ApprovalTask> | null;
  confirm_action_id?: string | null;
};

type MemorySuggestion = {
  content: string;
  memoryType: "PREFERENCE" | "FACT";
  status: "pending" | "saving" | "saved" | "failed";
  error?: string;
};

function uuid() {
  return crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatTime(value?: string) {
  if (!value) return "刚刚";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function titleFromMessage(content: string) {
  const compact = content.trim().replace(/\s+/g, " ");
  return compact.length > 28 ? `${compact.slice(0, 28)}…` : compact || "新对话";
}

function extractMemorySuggestion(content: string): MemorySuggestion | null {
  const match = content.match(/(?:请|麻烦)?(?:帮我)?记住[，,:：\s]*(.+)/);
  const remembered = match?.[1]?.trim().replace(/[。！!]$/, "");
  if (!remembered) return null;
  const isPreference = /偏好|倾向|希望|喜欢|优先|简洁/.test(remembered);
  return {
    content: remembered,
    memoryType: isPreference ? "PREFERENCE" : "FACT",
    status: "pending",
  };
}

function fromHistory(message: AgentMessage): ChatMessage {
  return {
    ...message,
    role: message.role.toLowerCase(),
    citations: message.citations || [],
    proposed_actions: message.proposed_actions || [],
    delivery_status: message.delivery_status || "sent",
  };
}

function assistantFromResponse(data: AgentResponse): ChatMessage {
  return {
    message_id: `assistant-${data.trace_id}`,
    role: "assistant",
    content: getResponseText(data),
    sequence_number: Number.MAX_SAFE_INTEGER,
    citations: data.citations || [],
    proposed_actions: data.proposed_actions || [],
    trace_id: data.trace_id,
    delivery_status: "sent",
    approval: (data.approval as Partial<ApprovalTask> | null) || null,
  };
}

function getResponseText(data: AgentResponse) {
  if (data.status === "PENDING_APPROVAL") {
    return data.message || "您的高风险操作需要人工审核，请耐心等待。";
  }
  if (data.proposed_actions?.length) {
    return data.message || "请确认以下操作。";
  }
  return data.message || "请问还有什么可以帮您的？";
}

export default function AgentPage() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [slowRequest, setSlowRequest] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [memorySuggestion, setMemorySuggestion] = useState<MemorySuggestion | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const mountedRef = useRef(true);
  const activeRequestRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);

  const pendingAction = useMemo(
    () => [...messages].reverse().flatMap(message => message.proposed_actions)
      .find(action => action.status.toLowerCase() === "pending_confirmation") || null,
    [messages],
  );

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    if (!sending) {
      setElapsedSeconds(0);
      setSlowRequest(false);
      return;
    }
    const started = Date.now();
    const interval = window.setInterval(
      () => setElapsedSeconds(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    const slowTimer = window.setTimeout(() => setSlowRequest(true), 15000);
    return () => {
      window.clearInterval(interval);
      window.clearTimeout(slowTimer);
    };
  }, [sending]);

  useEffect(() => {
    mountedRef.current = true;
    void restoreConversations();
    return () => {
      mountedRef.current = false;
    };
    // Restore once per authenticated page mount; later reloads are explicit user actions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function persistCurrentSession(id: string | null) {
    if (id) localStorage.setItem(LAST_SESSION_KEY, id);
    else localStorage.removeItem(LAST_SESSION_KEY);
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("session", id);
    else url.searchParams.delete("session");
    window.history.replaceState({}, "", `${url.pathname}${url.search}`);
  }

  async function restoreConversations() {
    const started = performance.now();
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const response = await agent.listSessions();
      const items = Array.isArray(response.data?.items) ? response.data.items : [];
      if (!mountedRef.current) return;
      setSessions(items);
      const requested = new URL(window.location.href).searchParams.get("session");
      const recent = localStorage.getItem(LAST_SESSION_KEY);
      const selected = [requested, recent, items[0]?.session_id]
        .find(id => id && items.some(item => item.session_id === id)) || null;
      if (selected) {
        setSessionId(selected);
        sessionIdRef.current = selected;
        persistCurrentSession(selected);
        await loadMessages(selected);
      } else {
        setMessages([]);
      }
      if (process.env.NODE_ENV === "development") {
        console.info("session_list_load_ms", Math.round(performance.now() - started));
      }
    } catch (error) {
      if (mountedRef.current) setHistoryError(friendlyError(error));
    } finally {
      if (mountedRef.current) setHistoryLoading(false);
    }
  }

  async function loadMessages(id: string) {
    const started = performance.now();
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const response = await agent.getMessages(id);
      const items = Array.isArray(response.data?.items) ? response.data.items : [];
      if (mountedRef.current && sessionIdRef.current === id) {
        setMessages(items.map(fromHistory));
      }
      if (process.env.NODE_ENV === "development") {
        console.info("history_load_ms", Math.round(performance.now() - started));
      }
    } catch (error) {
      if (mountedRef.current && sessionIdRef.current === id) {
        setHistoryError(friendlyError(error));
      }
    } finally {
      if (mountedRef.current) setHistoryLoading(false);
    }
  }

  async function chooseSession(id: string) {
    setDrawerOpen(false);
    setSessionId(id);
    sessionIdRef.current = id;
    persistCurrentSession(id);
    setMemorySuggestion(null);
    await loadMessages(id);
  }

  function startNewConversation() {
    setDrawerOpen(false);
    setSessionId(null);
    sessionIdRef.current = null;
    persistCurrentSession(null);
    setMessages([]);
    setHistoryError("");
    setMemorySuggestion(null);
  }

  async function send(
    rawMessage: string,
    confirmActionId: string | null = null,
    retryClientMessageId?: string | null,
  ) {
    const message = rawMessage.trim();
    if (!message || activeRequestRef.current) return;
    activeRequestRef.current = true;
    const started = performance.now();
    const clientMessageId = retryClientMessageId || uuid();
    const existingSessionId = sessionIdRef.current;
    const optimistic: ChatMessage = {
      message_id: `client-${clientMessageId}`,
      role: "user",
      content: message,
      sequence_number: Number.MAX_SAFE_INTEGER - 1,
      citations: [],
      proposed_actions: [],
      delivery_status: retryClientMessageId ? "retrying" : "sending",
      client_message_id: clientMessageId,
      confirm_action_id: confirmActionId,
    };
    setMessages(previous => {
      const withoutPreviousAttempt = previous.filter(
        item => item.client_message_id !== clientMessageId,
      );
      return [...withoutPreviousAttempt, optimistic];
    });
    setInput("");
    setSending(true);
    setHistoryError("");
    if (process.env.NODE_ENV === "development") {
      requestAnimationFrame(() => {
        console.info("optimistic_render_ms", Math.round(performance.now() - started));
      });
    }

    try {
      const response = existingSessionId
        ? await agent.sendMessage(
          existingSessionId, message, confirmActionId, clientMessageId,
        )
        : await agent.createSession(message, clientMessageId);
      const data = response.data;
      const resolvedSessionId = data.session_id;
      if (!mountedRef.current) return;
      if (!existingSessionId || sessionIdRef.current === existingSessionId) {
        setSessionId(resolvedSessionId);
        sessionIdRef.current = resolvedSessionId;
        persistCurrentSession(resolvedSessionId);
        setMessages(previous => {
          const sent = previous.map(item =>
            item.client_message_id === clientMessageId
              ? { ...item, delivery_status: "sent" as const }
              : confirmActionId
                ? {
                  ...item,
                  proposed_actions: item.proposed_actions.map(action =>
                    action.action_id === confirmActionId
                      ? { ...action, status: "CONSUMED" }
                      : action,
                  ),
                }
                : item,
          );
          return [...sent, assistantFromResponse(data)];
        });
        setSessions(previous => {
          const now = new Date().toISOString();
          const existing = previous.find(item => item.session_id === resolvedSessionId);
          const summary: AgentSession = {
            session_id: resolvedSessionId,
            title: existing?.title || titleFromMessage(message),
            status: "ACTIVE",
            message_count: (existing?.message_count || 0) + 2,
            last_message_preview: getResponseText(data).slice(0, 60),
            created_at: existing?.created_at || now,
            updated_at: now,
          };
          return [summary, ...previous.filter(item => item.session_id !== resolvedSessionId)];
        });
        const suggestion = extractMemorySuggestion(message);
        if (suggestion) setMemorySuggestion(suggestion);
        void loadMessages(resolvedSessionId);
      }
      if (process.env.NODE_ENV === "development") {
        console.info("request_total_ms", Math.round(performance.now() - started));
      }
    } catch (error) {
      if (mountedRef.current) {
        setMessages(previous => previous.map(item =>
          item.client_message_id === clientMessageId
            ? { ...item, delivery_status: "failed" as const }
            : item,
        ));
        setHistoryError(friendlyError(error));
      }
    } finally {
      activeRequestRef.current = false;
      if (mountedRef.current) setSending(false);
    }
  }

  async function saveMemory() {
    if (!memorySuggestion || memorySuggestion.status === "saving") return;
    setMemorySuggestion({ ...memorySuggestion, status: "saving" });
    try {
      await memories.create({
        memory_type: memorySuggestion.memoryType,
        content: memorySuggestion.content,
        key: memorySuggestion.memoryType === "PREFERENCE"
          ? "after_sales_preference"
          : undefined,
        source: "explicit_agent_confirmation",
      });
      setMemorySuggestion({ ...memorySuggestion, status: "saved" });
    } catch (error) {
      setMemorySuggestion({
        ...memorySuggestion,
        status: "failed",
        error: friendlyError(error),
      });
    }
  }

  const historyPanel = (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-semibold text-slate-900">历史对话</h2>
          <button
            onClick={startNewConversation}
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            新对话
          </button>
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          历史对话用于恢复本次交流；长期记忆用于跨对话记住你主动保存的偏好。
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {historyLoading && sessions.length === 0 && (
          <div aria-label="正在加载历史对话" className="space-y-2 p-2">
            {[1, 2, 3].map(item => (
              <div key={item} className="h-16 animate-pulse rounded-md bg-slate-100" />
            ))}
          </div>
        )}
        {!historyLoading && historyError && sessions.length === 0 && (
          <div className="p-4 text-center text-sm text-red-600">
            <p>加载对话失败</p>
            <button onClick={() => void restoreConversations()} className="mt-2 underline">
              重新加载
            </button>
          </div>
        )}
        {!historyLoading && !historyError && sessions.length === 0 && (
          <p className="p-6 text-center text-sm text-slate-500">暂无历史对话</p>
        )}
        <div className="space-y-1">
          {sessions.map(item => (
            <button
              key={item.session_id}
              onClick={() => void chooseSession(item.session_id)}
              className={`w-full rounded-md px-3 py-3 text-left transition ${
                item.session_id === sessionId
                  ? "bg-blue-50 text-blue-900"
                  : "text-slate-700 hover:bg-slate-50"
              }`}
            >
              <span className="block truncate text-sm font-medium">{item.title}</span>
              <span className="mt-1 flex justify-between text-xs text-slate-500">
                <span>{item.message_count} 条消息</span>
                <span>{formatTime(item.updated_at)}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <Navbar />
      <main className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 overflow-hidden md:px-4 md:py-5">
        <aside className="hidden w-64 shrink-0 overflow-hidden rounded-l-xl border border-r-0 border-slate-200 bg-white md:block">
          {historyPanel}
        </aside>
        {drawerOpen && (
          <div className="fixed inset-0 z-50 md:hidden">
            <button
              aria-label="关闭历史对话"
              className="absolute inset-0 bg-slate-950/40"
              onClick={() => setDrawerOpen(false)}
            />
            <aside className="relative h-full w-72 bg-white shadow-xl">{historyPanel}</aside>
          </div>
        )}
        <section className="flex min-w-0 flex-1 flex-col border-slate-200 bg-white md:rounded-r-xl md:border">
          <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setDrawerOpen(true)}
                className="rounded-md border border-slate-200 px-3 py-2 text-sm md:hidden"
              >
                历史对话
              </button>
              <div>
                <h1 className="font-semibold text-slate-900">ResolveAI 智能客服</h1>
                <p className="text-xs text-slate-500">此内容不会自动保存为长期记忆</p>
              </div>
            </div>
            <Link href="/memories" className="text-sm font-medium text-blue-700 hover:underline">
              查看记忆
            </Link>
          </header>

          <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
            {historyLoading && sessionId && messages.length === 0 && (
              <div aria-label="正在加载对话" className="space-y-4">
                <div className="h-16 w-2/3 animate-pulse rounded-lg bg-slate-100" />
                <div className="ml-auto h-14 w-1/2 animate-pulse rounded-lg bg-blue-50" />
              </div>
            )}
            {!historyLoading && messages.length === 0 && (
              <div className="mx-auto mt-16 max-w-md text-center text-slate-500">
                <p className="text-lg font-medium text-slate-700">欢迎使用 ResolveAI 智能客服</p>
                <p className="mt-2 text-sm">可以询问订单、物流、退款与售后政策问题。</p>
              </div>
            )}
            <div className="space-y-4" aria-live="polite">
              {messages.map(message => (
                <div
                  key={message.message_id}
                  className={message.role === "user" ? "text-right" : "text-left"}
                >
                  <div className={`inline-block max-w-[88%] rounded-xl px-4 py-3 text-left text-sm md:max-w-[78%] ${
                    message.role === "user"
                      ? "bg-blue-600 text-white"
                      : "border border-slate-200 bg-white text-slate-800"
                  }`}>
                    <p className="whitespace-pre-wrap leading-6">{message.content}</p>
                    {message.role === "user" && message.delivery_status !== "sent" && (
                      <div className="mt-2 text-xs text-blue-100">
                        {message.delivery_status === "sending" && "正在发送"}
                        {message.delivery_status === "retrying" && "正在重试"}
                        {message.delivery_status === "failed" && (
                          <span>
                            发送失败 ·{" "}
                            <button
                              onClick={() => void send(
                                message.content,
                                message.confirm_action_id || null,
                                message.client_message_id,
                              )}
                              className="font-semibold underline"
                            >
                              重新发送
                            </button>
                          </span>
                        )}
                      </div>
                    )}
                    {message.citations.length > 0 && (
                      <div className="mt-3 border-t border-slate-200 pt-3">
                        <p className="text-xs font-semibold text-slate-600">政策引用</p>
                        {message.citations.map(citation => (
                          <div key={`${citation.policy_key}-${citation.version}`} className="mt-2 text-xs leading-5 text-slate-500">
                            <span className="rounded bg-slate-100 px-1 font-mono">{citation.policy_key}</span>{" "}
                            v{citation.version} · {citation.title}
                            {citation.source && (
                              <span> · {citation.source === "legal_requirement" ? "法律规则" : "平台规则"}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {message.proposed_actions.map(action => (
                      <div key={action.action_id} className="mt-3 rounded-md bg-blue-50 p-3 text-xs text-slate-700">
                        <p className="font-semibold">待确认操作：{action.description}</p>
                        <p className="mt-1 text-slate-500">状态：{labelFor(action.status)}</p>
                      </div>
                    ))}
                    {message.approval && (
                      <div className="mt-3 rounded-md bg-amber-50 p-3 text-xs text-amber-800">
                        等待人工审批 · {labelFor(message.approval.status)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="text-left" role="status">
                  <div className="inline-block rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                    <p>AI 正在分析你的问题…</p>
                    {elapsedSeconds > 0 && <p className="mt-1 text-xs">已等待 {elapsedSeconds} 秒</p>}
                    {slowRequest && <p className="mt-1 text-xs text-amber-700">处理时间较长，请稍候</p>}
                  </div>
                </div>
              )}
              {memorySuggestion && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-slate-700">
                  <p className="font-medium">是否保存为长期记忆？</p>
                  <p className="mt-1 text-slate-600">{memorySuggestion.content}</p>
                  {memorySuggestion.status === "saved" ? (
                    <p className="mt-2 font-medium text-green-700">已保存到长期记忆</p>
                  ) : (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        onClick={() => void saveMemory()}
                        disabled={memorySuggestion.status === "saving"}
                        className="rounded-md bg-blue-600 px-3 py-2 font-medium text-white disabled:opacity-50"
                      >
                        {memorySuggestion.status === "saving" ? "正在保存" : "记住这条偏好"}
                      </button>
                      <button onClick={() => setMemorySuggestion(null)} className="rounded-md border border-slate-300 px-3 py-2">
                        暂不保存
                      </button>
                    </div>
                  )}
                  {memorySuggestion.status === "failed" && (
                    <p className="mt-2 text-red-600">{memorySuggestion.error || "保存失败"}</p>
                  )}
                </div>
              )}
              {pendingAction && (
                <div className="flex justify-center gap-3">
                  <button
                    onClick={() => void send(`确认执行 ${pendingAction.description}`, pendingAction.action_id)}
                    disabled={sending}
                    className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                  >
                    确认执行
                  </button>
                  <button
                    onClick={() => setMessages(previous => previous.map(item => ({
                      ...item,
                      proposed_actions: item.proposed_actions.map(action =>
                        action.action_id === pendingAction.action_id
                          ? { ...action, status: "CANCELLED" }
                          : action,
                      ),
                    })))}
                    disabled={sending}
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 disabled:opacity-50"
                  >
                    取消
                  </button>
                </div>
              )}
              {historyError && messages.length > 0 && (
                <p className="text-center text-sm text-red-600">{historyError}</p>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <form
            className="border-t border-slate-200 bg-white p-4"
            onSubmit={event => {
              event.preventDefault();
              void send(input);
            }}
          >
            <div className="mx-auto flex max-w-4xl gap-3">
              <label htmlFor="agent-message" className="sr-only">输入您的问题</label>
              <input
                id="agent-message"
                value={input}
                onChange={event => setInput(event.target.value)}
                placeholder="输入您的问题..."
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-4 py-3 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="rounded-lg bg-blue-600 px-5 py-3 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                发送
              </button>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}
