interface APIResponse<T = any> {
  success: boolean;
  code: string;
  message: string;
  data: T | null;
}

interface UserInfo {
  id: string; email: string; full_name: string; role: string;
}

interface Product {
  id: string; name: string; category: string; price: string; stock: number; is_returnable: boolean;
}

interface OrderItem {
  id: string; product_name: string; quantity: number; unit_price: string;
}

interface Order {
  id: string; order_number: string; status: string; total_amount: string; paid_amount: string;
  shipping_fee: string; paid_at?: string; shipped_at?: string; delivered_at?: string; items: OrderItem[];
}

interface LogisticsInfo {
  id: string; carrier: string; tracking_number: string; status: string;
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

interface Memory {
  id: string; memory_type: string; key?: string; content: string; source: string; confidence: number;
  status: string; version: number; created_at?: string;
}

interface Approval {
  id: string; action_id: string; tool_name: string; approval_type: string; status: string;
  risk_level: string; reason?: string; decision_reason?: string; created_at?: string;
}

interface PaginatedResponse<T> {
  items: T[]; total: number; page: number; page_size: number; total_pages: number;
}
