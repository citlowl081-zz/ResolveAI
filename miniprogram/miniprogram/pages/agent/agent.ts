import { api } from "../../services/api";
import { fmtDate, uuid } from "../../utils/util";

const LAST_SESSION_KEY = "resolveai_last_agent_session_id";
const AGENT_SUGGESTION_KEY = "resolveai_agent_suggested_question";

interface ChatMessage extends AgentMessage {
  action?: ProposedAction | null;
  approval?: Partial<Approval> | null;
  confirmActionId?: string | null;
  hasCitations: boolean;
}

interface MemorySuggestion {
  content: string;
  memoryType: "PREFERENCE" | "FACT";
  status: "pending" | "saving" | "saved" | "failed";
  error?: string;
}

interface SessionView extends AgentSession {
  updatedText: string;
}

function sessionView(session: AgentSession): SessionView {
  return { ...session, updatedText: fmtDate(session.updated_at || session.created_at) };
}

let requestActive = false;
let waitTimer: number | null = null;

function extractMemorySuggestion(content: string): MemorySuggestion | null {
  const match = content.match(/(?:请|麻烦)?(?:帮我)?记住[，,:：\s]*(.+)/);
  const remembered = match?.[1]?.trim().replace(/[。！!]$/, "");
  if (!remembered) return null;
  if (/密码|验证码|API\s*Key|身份证|银行卡|完整地址|健康|病史|临时订单状态/i.test(remembered)) {
    return null;
  }
  return {
    content: remembered,
    memoryType: /偏好|倾向|希望|喜欢|优先/.test(remembered) ? "PREFERENCE" : "FACT",
    status: "pending",
  };
}

function historyMessage(message: AgentMessage): ChatMessage {
  const actions = message.proposed_actions || [];
  return {
    ...message,
    role: message.role.toLowerCase(),
    citations: message.citations || [],
    hasCitations: Boolean(message.citations?.length),
    proposed_actions: actions,
    action: actions.find((item) => item.status.toLowerCase() === "pending_confirmation") || null,
    delivery_status: message.delivery_status || "sent",
  };
}

function responseMessage(data: AgentTurnResponse): ChatMessage {
  const content = data.status === "PENDING_APPROVAL"
    ? data.message || "您的高风险操作需要人工审核，请耐心等待。"
    : data.message || (data.proposed_actions?.length ? "请确认以下操作。" : "请问还有什么可以帮您的？");
  const action = data.proposed_actions?.find(
    (item) => item.status.toLowerCase() === "pending_confirmation",
  ) || null;
  return {
    message_id: `assistant-${data.trace_id || uuid()}`,
    role: "assistant",
    content,
    sequence_number: Number.MAX_SAFE_INTEGER,
    citations: data.citations || [],
    hasCitations: Boolean(data.citations?.length),
    proposed_actions: data.proposed_actions || [],
    action,
    approval: data.approval || null,
    trace_id: data.trace_id,
    delivery_status: "sent",
  };
}

Page({
  data: {
    sessions: [] as SessionView[],
    messages: [] as ChatMessage[],
    input: "",
    sending: false,
    historyLoading: true,
    historyError: "",
    sessionId: "",
    pendingAction: null as ProposedAction | null,
    pendingMemory: null as MemorySuggestion | null,
    waitSeconds: 0,
    showSessions: false,
  },

  onShow() {
    const suggestion = wx.getStorageSync(AGENT_SUGGESTION_KEY) as string;
    if (suggestion) {
      if (!this.data.input) this.setData({ input: suggestion });
      wx.removeStorageSync(AGENT_SUGGESTION_KEY);
    }
    void this.restoreConversations();
  },

  onUnload() {
    if (waitTimer !== null) clearInterval(waitTimer);
    waitTimer = null;
  },

  onInput(event: WechatMiniprogram.Input) {
    this.setData({ input: event.detail.value });
  },

  toggleSessions() {
    this.setData({ showSessions: !this.data.showSessions });
  },

  async restoreConversations() {
    if (this.data.sending) return;
    this.setData({ historyLoading: true, historyError: "" });
    try {
      const response = await api.agent.listSessions();
      const sessions = (response.data.data?.items || []).map(sessionView);
      const recent = wx.getStorageSync(LAST_SESSION_KEY) as string;
      const selected = [this.data.sessionId, recent, sessions[0]?.session_id]
        .find((id) => id && sessions.some((session) => session.session_id === id)) || "";
      this.setData({ sessions, sessionId: selected });
      if (selected) await this.loadMessages(selected);
      else this.setData({ messages: [], pendingAction: null });
    } catch (error) {
      this.setData({ historyError: (error as Error).message });
    } finally {
      this.setData({ historyLoading: false });
    }
  },

  async loadMessages(sessionId: string) {
    try {
      const response = await api.agent.getMessages(sessionId);
      if (this.data.sessionId !== sessionId) return;
      const messages = (response.data.data?.items || []).map(historyMessage);
      const pendingAction = [...messages].reverse()
        .map((message) => message.action)
        .find((action) => action?.status.toLowerCase() === "pending_confirmation") || null;
      this.setData({ messages, pendingAction, historyError: "" });
    } catch (error) {
      this.setData({ historyError: (error as Error).message });
    }
  },

  async chooseSession(event: WechatMiniprogram.TouchEvent) {
    const sessionId = event.currentTarget.dataset.id as string;
    if (!sessionId || requestActive) return;
    wx.setStorageSync(LAST_SESSION_KEY, sessionId);
    this.setData({
      sessionId, messages: [], pendingAction: null, pendingMemory: null,
      showSessions: false, historyLoading: true,
    });
    await this.loadMessages(sessionId);
    this.setData({ historyLoading: false });
  },

  startNewSession() {
    if (requestActive) return;
    wx.removeStorageSync(LAST_SESSION_KEY);
    this.setData({
      sessionId: "", messages: [], pendingAction: null, pendingMemory: null,
      historyError: "", showSessions: false,
    });
  },

  doSend() {
    void this.send(this.data.input);
  },

  async send(rawMessage: string, confirmActionId: string | null = null, retryClientMessageId?: string) {
    const message = rawMessage.trim();
    if (!message || requestActive) return;
    requestActive = true;
    const clientMessageId = retryClientMessageId || uuid();
    const optimistic: ChatMessage = {
      message_id: `client-${clientMessageId}`,
      role: "user",
      content: message,
      sequence_number: Number.MAX_SAFE_INTEGER - 1,
      citations: [],
      hasCitations: false,
      proposed_actions: [],
      delivery_status: retryClientMessageId ? "retrying" : "sending",
      client_message_id: clientMessageId,
      confirmActionId,
    };
    const messages = this.data.messages.filter(
      (item) => item.client_message_id !== clientMessageId,
    );
    this.setData({
      messages: [...messages, optimistic], input: "", sending: true,
      historyError: "", waitSeconds: 0,
    });
    waitTimer = setInterval(() => {
      this.setData({ waitSeconds: this.data.waitSeconds + 1 });
    }, 1000) as unknown as number;

    try {
      const response = this.data.sessionId
        ? await api.agent.sendMessage(
          this.data.sessionId, message, confirmActionId, clientMessageId,
        )
        : await api.agent.createSession(message, clientMessageId);
      const data = response.data.data;
      if (!data) throw new Error("系统暂时无法处理，请稍后重试");
      const sessionId = data.session_id;
      wx.setStorageSync(LAST_SESSION_KEY, sessionId);
      const sentMessages = this.data.messages.map((item) => {
        if (item.client_message_id === clientMessageId) {
          return { ...item, delivery_status: "sent" as DeliveryStatus };
        }
        if (confirmActionId && item.action?.action_id === confirmActionId) {
          const consumed = { ...item.action, status: "CONSUMED" };
          return { ...item, action: consumed, proposed_actions: [consumed] };
        }
        return item;
      });
      const assistant = responseMessage(data);
      this.setData({
        sessionId,
        messages: [...sentMessages, assistant],
        pendingAction: assistant.action || null,
        pendingMemory: extractMemorySuggestion(message),
      });
      await this.refreshSessionSummaries(sessionId);
      await this.loadMessages(sessionId);
    } catch (error) {
      this.setData({
        messages: this.data.messages.map((item) => item.client_message_id === clientMessageId
          ? { ...item, delivery_status: "failed" as DeliveryStatus }
          : item),
        historyError: (error as Error).message,
      });
    } finally {
      requestActive = false;
      if (waitTimer !== null) clearInterval(waitTimer);
      waitTimer = null;
      this.setData({ sending: false, waitSeconds: 0 });
    }
  },

  async refreshSessionSummaries(activeSessionId: string) {
    try {
      const response = await api.agent.listSessions();
      this.setData({
        sessions: (response.data.data?.items || []).map(sessionView),
        sessionId: activeSessionId,
      });
    } catch {
      // The completed message remains visible even if summary refresh fails.
    }
  },

  retry(event: WechatMiniprogram.TouchEvent) {
    const clientMessageId = event.currentTarget.dataset.id as string;
    const message = this.data.messages.find((item) => item.client_message_id === clientMessageId);
    if (message) void this.send(message.content, message.confirmActionId || null, clientMessageId);
  },

  confirm() {
    const action = this.data.pendingAction;
    if (action) void this.send(`确认执行 ${action.description}`, action.action_id);
  },

  decline() {
    const action = this.data.pendingAction;
    if (!action) return;
    this.setData({
      pendingAction: null,
      messages: this.data.messages.map((message) => message.action?.action_id === action.action_id
        ? { ...message, action: null, proposed_actions: [{ ...action, status: "CANCELLED" }] }
        : message),
    });
  },

  async confirmMemory() {
    const suggestion = this.data.pendingMemory;
    if (!suggestion || suggestion.status === "saving") return;
    this.setData({ pendingMemory: { ...suggestion, status: "saving" } });
    try {
      await api.memories.create({
        memory_type: suggestion.memoryType,
        content: suggestion.content,
        key: suggestion.memoryType === "PREFERENCE" ? "after_sales_preference" : undefined,
        source: "explicit_agent_confirmation",
        confidence: 1,
      });
      this.setData({ pendingMemory: { ...suggestion, status: "saved" } });
    } catch (error) {
      this.setData({
        pendingMemory: { ...suggestion, status: "failed", error: (error as Error).message },
      });
    }
  },

  dismissMemory() {
    this.setData({ pendingMemory: null });
  },
});
