interface APIResponse<T = unknown> {
  success: boolean;
  code: string;
  message: string;
  data: T | null;
}

interface UserInfo {
  id: string; email: string; full_name: string; role: string;
}

interface Product {
  id: string; name: string; description?: string | null; category: string; price: string;
  stock: number; image_url?: string | null; is_returnable: boolean;
}

interface CatalogProduct extends Product {
  categoryLabel: string; categoryKey: string;
}

interface CartItem {
  product: Product; quantity: number; selected: boolean;
}

interface OrderItem {
  id: string; product_name: string; quantity: number; unit_price: string;
}

interface Order {
  id: string; order_number: string; status: string; total_amount: string; paid_amount: string;
  shipping_fee: string; paid_at?: string; shipped_at?: string; delivered_at?: string; items: OrderItem[];
}

interface LogisticsInfo {
  id: string; order_id: string; carrier: string; tracking_number: string; status: string;
  current_location?: string | null; estimated_delivery?: string | null;
  actual_delivery?: string | null; events?: LogisticsEvent[];
}

interface LogisticsEvent {
  timestamp: string; status: string; location: string; description: string;
}

interface Ticket {
  id: string; ticket_number: string; intent: string; status: string; reject_reason?: string; version: number;
}

interface Citation {
  policy_key: string; version: number; title: string; category: string; snippet: string; similarity_score: number;
}

interface ProposedAction {
  action_id: string; tool_name: string; description: string; status: string; expires_at?: string;
}

type DeliveryStatus = "sending" | "sent" | "failed" | "retrying";

interface AgentMessage {
  message_id: string; role: string; content: string; sequence_number: number;
  citations: Citation[]; proposed_actions: ProposedAction[]; trace_id?: string | null;
  delivery_status: DeliveryStatus; client_message_id?: string | null; created_at?: string;
}

interface AgentSession {
  session_id: string; title: string; status: string; message_count: number;
  last_message_preview: string; created_at?: string; updated_at?: string;
}

interface AgentTurnResponse {
  session_id: string; message?: string; messages?: AgentMessage[];
  proposed_actions: ProposedAction[]; citations: Citation[]; trace_id: string;
  status?: string; approval?: Partial<Approval> | null;
}

interface Memory {
  id: string; memory_type: string; key?: string; content: string; source: string; confidence: number;
  status: string; version: number; created_at?: string;
}

interface MemoryCreateInput {
  memory_type: string; content: string; key?: string; source?: string; confidence?: number;
}

interface MemoryUpdateInput {
  content?: string; confidence?: number; status?: string;
}

interface Approval {
  id: string; user_id: string; agent_session_id?: string | null; turn_id?: string | null;
  action_id: string; tool_name: string; approval_type: string; status: string;
  risk_level: string; reason?: string | null; requested_by: string; decided_by?: string | null;
  decision_reason?: string | null; expires_at?: string | null; decided_at?: string | null;
  version: number; created_at?: string | null; updated_at?: string | null;
}

interface PaginatedResponse<T> {
  items: T[]; total: number; page: number; page_size: number; total_pages: number;
}
