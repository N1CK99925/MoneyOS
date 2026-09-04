export interface CatalogItem {
  id: string
  name: string
  price_paise: number
  price_inr: number
  description?: string
  image?: string
  category?: string
}

export interface CatalogCategory {
  name: string
  products: CatalogItem[]
}

export interface Catalog {
  merchant: string
  currency: string
  products: CatalogItem[]
  categories?: CatalogCategory[]
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

export interface SystemSetting {
  key: string
  value: string
  default: string
  description: string
  updated_at: string
}
