export interface Product {
  id: string;
  name: string;
  price_paise: number;
  currency: string;
  description: string;
}

export interface CatalogResponse {
  merchant: string;
  currency: string;
  products: Product[];
}

export interface CartItem {
  item_id: string;
  quantity: number;
}

export interface CheckoutSessionItem {
  id: string;
  name: string;
  price_paise: number;
  quantity: number;
  line_total_paise: number;
}

export interface CheckoutSession {
  session_id: string;
  razorpay_order_id: string;
  items: CheckoutSessionItem[];
  total_paise: number;
  currency: string;
  status: "not_ready_for_payment" | "ready_for_payment" | "completed" | "canceled";
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  actor: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  payload: string | null;
  result: string | null;
  error_reason: string | null;
  signed_hash: string | null;
}

// Agent types

export interface AgentToolCall {
  type: "tool_call";
  name: string;
  args: Record<string, unknown>;
}

export interface AgentToolResult {
  type: "tool_result";
  name: string;
  result: string;
}

export interface AgentModelSwitch {
  type: "model_switch";
  model: string;
}

export interface AgentSummary {
  type: "summary";
  message: string;
}

export interface AgentError {
  type: "error";
  message: string;
}

export type AgentEvent =
  | AgentToolCall
  | AgentToolResult
  | AgentModelSwitch
  | AgentSummary
  | AgentError;
