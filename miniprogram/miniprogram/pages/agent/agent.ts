import { api } from "../../services/api";
import { uuid } from "../../utils/util";

interface Msg { role: string; content: string; citations?: Citation[]; action?: ProposedAction | null; approval?: any; }

Page({
  data: {
    messages: [] as Msg[], input: "", sending: false,
    sessionId: "", pendingAction: null as ProposedAction | null,
  },
  onInput(e: any) { this.setData({ input: e.detail.value }); },
  async doSend() {
    const msg = this.data.input.trim();
    if (!msg || this.data.sending) return;
    this.setData({ input: "", sending: true });
    try {
      let res: any;
      const idemKey = uuid();
      if (!this.data.sessionId) {
        res = await api.agent.createSession(msg, idemKey);
        if (res.success && res.data) { this.setData({ sessionId: res.data.session_id }); }
      } else {
        res = await api.agent.sendMessage(this.data.sessionId, msg, null, idemKey);
      }
      const d = res.data || res;
      const citations = d.citations || [];
      const actions = d.proposed_actions || [];
      const action = actions.length > 0 ? actions[0] : null;
      const msgs: Msg[] = [
        ...this.data.messages,
        { role: "user", content: msg },
        { role: "assistant", content: d.message || "请问还有什么可以帮您的？", citations, action, approval: d.approval || null },
      ];
      this.setData({ messages: msgs, pendingAction: action?.status === "pending_confirmation" ? action : null });
      if (d.session_id) this.setData({ sessionId: d.session_id });
    } catch (e: any) {
      this.setData({ messages: [...this.data.messages, { role: "user", content: msg }, { role: "system", content: `错误: ${e.message}` }] });
    } finally { this.setData({ sending: false }); }
  },
  async confirm() {
    const pa = this.data.pendingAction;
    if (!pa) return;
    this.setData({ sending: true, pendingAction: null });
    try {
      const idemKey = uuid();
      const res = await api.agent.sendMessage(this.data.sessionId, `确认 ${pa.description}`, pa.action_id, idemKey);
      const d = res.data || res;
      this.setData({ messages: [...this.data.messages, { role: "assistant", content: d.message || "已处理", approval: d.approval || null }] });
    } catch (e: any) {
      this.setData({ messages: [...this.data.messages, { role: "system", content: `确认失败: ${e.message}` }] });
    } finally { this.setData({ sending: false }); }
  },
  decline() {
    this.setData({ pendingAction: null, messages: [...this.data.messages, { role: "system", content: "已取消操作。" }] });
  },
});
