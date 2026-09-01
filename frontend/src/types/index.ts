export interface CatalogItem {
  id: string
  name: string
  price_paise: number
  price_inr: number
  description?: string
  image?: string
}

export interface CheckoutSession {
  id: string
  status: 'created' | 'pending' | 'completed' | 'cancelled'
  item_id: string
  item_name: string
  amount: number
  razorpay_order_id?: string
  razorpay_payment_id?: string
}

export type AgentMessageType = 'message' | 'progress'

export interface AgentMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  type?: AgentMessageType
}

export interface AuditEntry {
  id: number
  timestamp: string
  actor: string
  action: string
  entity_type?: string
  entity_id?: string
  payload?: string
  result?: string
  error_reason?: string
  signed_hash?: string
}
