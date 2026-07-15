// ── API Response envelope ──
export interface APIResponse<T = unknown> {
  success: boolean;
  code: string;
  message: string;
  data: T | null;
  trace_id?: string | null;
}

// ── Auth ──
export interface UserInfo {
  id: string; email: string; full_name: string; role: string;
  phone?: string | null; default_address?: string | null;
}
export interface TokenData { access_token: string; refresh_token: string; token_type: string; }

// ── Core types ──
export interface Product { id: string; name: string; category: string; price: string; stock: number; is_returnable: boolean; }
export interface Order { id: string; order_number: string; status: string; total_amount: string; items?: { product_name: string; quantity: number; unit_price: string; }[]; }
export interface Ticket { id: string; ticket_number: string; order_id: string; intent: string; status: string; reject_reason?: string | null; version: number; created_at?: string; }
export interface Policy { id?: string; policy_key: string; version: number; title: string; category: string; content?: string; content_summary?: string | null; status: string; effective_date: string; source?: string | null; }
export interface ApprovalTask { id: string; user_id: string; action_id: string; tool_name: string; approval_type: string; status: string; risk_level: string; reason?: string | null; decision_reason?: string | null; decided_by?: string | null; version: number; expires_at?: string | null; decided_at?: string | null; created_at?: string; }
export interface AgentTrace { id: string; session_id: string; turn_id: string; trace_id: string; node_name: string; sequence: number; duration_ms: number; is_success: boolean; routing_decision?: string | null; error_code?: string | null; llm_call?: Record<string, unknown> | null; created_at?: string; }
export interface ToolLog { id: string; tool_name: string; is_success: boolean; duration_ms: number; error_message?: string | null; created_at?: string; }
export interface PaginatedResponse<T> { items: T[]; total: number; page: number; page_size: number; total_pages: number; }
