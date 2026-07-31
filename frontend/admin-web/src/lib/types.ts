export interface APIResponse<T = unknown> {
  success: boolean;
  code: string;
  message: string;
  data: T;
  trace_id?: string | null;
}
export interface UserInfo {
  id: string;
  email: string;
  full_name: string;
  role: string;
}
export interface TokenData {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
export interface Product {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  price: string;
  stock: number;
  image_url?: string | null;
  is_returnable: boolean;
  version?: number;
}
export interface Ticket {
  id: string;
  ticket_number: string;
  user_id?: string;
  order_id: string;
  intent: string;
  status: string;
  customer_request?: string | null;
  requested_items?: Record<string, unknown> | Record<string, unknown>[];
  reject_reason?: string | null;
  operator_notes?: string | null;
  version: number;
  created_at?: string;
  updated_at?: string;
}
export interface Policy {
  id?: string;
  policy_key: string;
  version: number;
  title: string;
  category: string;
  issue_types?: string[];
  content?: string;
  content_summary?: string | null;
  status: string;
  effective_date: string;
  source?: string | null;
  updated_at?: string;
}
export interface ApprovalTask {
  id: string;
  user_id: string;
  action_id: string;
  tool_name: string;
  approval_type: string;
  status: string;
  risk_level: string;
  reason?: string | null;
  decision_reason?: string | null;
  decided_by?: string | null;
  version: number;
  expires_at?: string | null;
  decided_at?: string | null;
  created_at?: string;
}
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
  llm_call?: Record<string, unknown> | null;
  tool_calls_summary?: Record<string, unknown>[] | null;
  created_at?: string;
}
export interface ToolLog {
  id: string;
  trace_id: string;
  session_id: string;
  tool_name: string;
  is_success: boolean;
  duration_ms: number;
  retry_count?: number;
  error_code?: string | null;
  error_message?: string | null;
  created_at?: string;
}
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
export interface DashboardMetrics {
  range_days: number;
  pending_tickets: number;
  today_tickets: number;
  pending_approvals: number;
  agent_sessions: number;
  policy_searches: number;
  failed_tool_calls: number;
  ticket_trend: { date: string; count: number }[];
  ticket_statuses: { status: string; count: number }[];
  intent_types: { intent: string; count: number }[];
  recent_high_risk_approvals: Record<string, string>[];
  recent_failed_tools: Record<string, string | number | null>[];
}
export interface AdminOrder {
  id: string;
  order_number: string;
  user_id: string;
  user_name: string;
  item_summary: string;
  paid_amount: string;
  status: string;
  logistics_status?: string | null;
  ticket_count: number;
  created_at?: string;
}
export interface AdminOrderDetail extends AdminOrder {
  total_amount: string;
  discount_amount: string;
  shipping_fee: string;
  paid_at?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  items: {
    id: string;
    product_id: string;
    product_name: string;
    unit_price: string;
    quantity: number;
    subtotal: string;
  }[];
  logistics?: {
    status: string;
    carrier: string;
    tracking_number: string;
    current_location?: string | null;
  } | null;
  tickets: {
    id: string;
    ticket_number: string;
    intent: string;
    status: string;
    created_at?: string;
  }[];
}
export interface AdminUser {
  id: string;
  full_name: string;
  email: string;
  role: string;
  risk_level: string;
  is_active: boolean;
  order_count: number;
  ticket_count: number;
  memory_count: number;
  created_at?: string;
}
export interface AdminUserDetail extends AdminUser {
  orders: Record<string, string>[];
  tickets: Record<string, string>[];
  memories: Record<string, string>[];
  sessions: Record<string, string | number>[];
}
export interface SystemStatus {
  backend: string;
  database: string;
  provider: string;
  model: string;
  embedding_provider: string;
  api_key_configured: boolean;
  base_url_configured: boolean;
  active_policy_count: number;
  latest_policy_update?: string | null;
  latest_seed?: string | null;
  latest_tool_failure?: string | null;
  app_version: string;
}
