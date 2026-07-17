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
  id: string;
  email: string;
  full_name: string;
  role: string;
  phone?: string | null;
  default_address?: string | null;
}

export interface TokenData {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ── Product ──
export interface Product {
  id: string;
  name: string;
  category: string;
  price: string;
  stock: number;
  is_returnable: boolean;
  created_at?: string;
}

// ── Order ──
export interface OrderItem {
  id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  refunded_quantity: number;
  reshipped_quantity: number;
}

export interface Order {
  id: string;
  order_number: string;
  status: string;
  total_amount: string;
  paid_amount: string;
  shipping_fee: string;
  paid_at?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  items: OrderItem[];
  created_at?: string;
}

// ── Logistics ──
export interface LogisticsInfo {
  id: string;
  order_id: string;
  carrier: string;
  tracking_number: string;
  status: string;
  events?: LogisticsEvent[];
}

export interface LogisticsEvent {
  status: string;
  location: string;
  timestamp: string;
  description: string;
}

// ── Ticket ──
export interface Ticket {
  id: string;
  ticket_number: string;
  order_id: string;
  intent: string;
  status: string;
  resolution_type?: string | null;
  customer_request?: string;
  reject_reason?: string | null;
  reject_code?: string | null;
  version: number;
  created_at?: string;
  updated_at?: string;
  completed_at?: string | null;
}

// ── Agent ──
export interface ProposedAction {
  action_id: string;
  tool_name: string;
  description: string;
  status: string;
  expires_at?: string;
}

export interface Citation {
  policy_key: string;
  version: number;
  title: string;
  category: string;
  snippet: string;
  similarity_score: number;
  source?: string;
}

export interface AgentMessage {
  role: string;
  content: string;
  sequence_number: number;
  turn_sequence: number;
  tool_calls?: unknown;
  tool_call_id?: string | null;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface AgentSession {
  id: string;
  user_id: string;
  status: string;
  message_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface AgentResponse {
  session_id: string;
  messages?: AgentMessage[];
  proposed_actions?: ProposedAction[];
  citations?: Citation[];
  status?: string;
  approval?: Record<string, unknown> | null;
  message?: string;
  trace_id: string;
}

// ── Memory ──
export interface UserMemory {
  id: string;
  memory_type: string;
  key?: string | null;
  content: string;
  structured_data?: Record<string, unknown> | null;
  source: string;
  confidence: number;
  status: string;
  version: number;
  created_at?: string | null;
  updated_at?: string | null;
}

// ── Approval ──
export interface ApprovalTask {
  id: string;
  user_id: string;
  agent_session_id?: string | null;
  action_id: string;
  tool_name: string;
  approval_type: string;
  status: string;
  risk_level: string;
  reason?: string | null;
  decided_by?: string | null;
  decision_reason?: string | null;
  expires_at?: string | null;
  decided_at?: string | null;
  version: number;
  created_at?: string | null;
}

// ── Pagination ──
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Policy ──
export interface Policy {
  id?: string;
  policy_key: string;
  version: number;
  title: string;
  category: string;
  content?: string;
  content_summary?: string | null;
  status: string;
  effective_date: string;
  expiration_date?: string | null;
  source?: string | null;
}

// ── Agent Trace ──
export interface AgentTrace {
  id: string;
  session_id: string;
  turn_id: string;
  trace_id: string;
  node_name: string;
  sequence: number;
  duration_ms: number;
  is_success: boolean;
  routing_decision?: string | null;
  error_code?: string | null;
  error_detail?: Record<string, unknown> | null;
  llm_call?: Record<string, unknown> | null;
  tool_calls_summary?: unknown;
  created_at?: string;
}

// ── Tool Log ──
export interface ToolLog {
  id: string;
  session_id: string;
  turn_id: string;
  message_id: string;
  tool_call_id: string;
  tool_name: string;
  tool_input?: Record<string, unknown> | null;
  tool_output?: Record<string, unknown> | null;
  is_success: boolean;
  error_code?: string | null;
  error_message?: string | null;
  duration_ms: number;
  retry_count: number;
  created_at?: string;
}

// ── Dashboard ──
export interface DashboardData {
  tickets_total: number;
  pending_approvals: number;
  active_sessions: number;
  tickets_by_status: Record<string, number>;
}
