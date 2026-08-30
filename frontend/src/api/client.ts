import type {
  CatalogResponse,
  CheckoutSession,
  AuditLogEntry,
  CartItem,
  AgentEvent,
} from "../types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail?.toString() ?? res.statusText);
  }
  return res.json();
}

export function fetchCatalog(): Promise<CatalogResponse> {
  return request<CatalogResponse>("/catalog");
}

export function createCheckoutSession(
  items: CartItem[],
  buyer_agent_id = "web-user"
): Promise<CheckoutSession> {
  return request<CheckoutSession>("/checkout_sessions", {
    method: "POST",
    body: JSON.stringify({ items, buyer_agent_id }),
  });
}

export function getCheckoutSession(session_id: string): Promise<CheckoutSession> {
  return request<CheckoutSession>(`/checkout_sessions/${session_id}`);
}

export function completeCheckout(session_id: string): Promise<CheckoutSession> {
  return request<CheckoutSession>(`/checkout_sessions/${session_id}/complete`, {
    method: "POST",
  });
}

export function cancelCheckout(session_id: string): Promise<{ status: string }> {
  return request(`/checkout_sessions/${session_id}/cancel`, { method: "POST" });
}

export function fetchAuditLog(limit = 50): Promise<AuditLogEntry[]> {
  return request<AuditLogEntry[]>(`/audit?limit=${limit}`);
}

export function fetchRazorpayKey(): Promise<{ key_id: string }> {
  return request<{ key_id: string }>("/razorpay_key");
}

export function runAgent(
  goal: string,
  onEvent: (event: AgentEvent) => void
): { abort: () => void } {
  const controller = new AbortController();

  fetch(`${BASE}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.ok) {
      onEvent({ type: "error", message: `HTTP ${res.status}` });
      return;
    }
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop()!;

      let eventType = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const data = line.slice(6);
          try {
            const parsed = JSON.parse(data);
            onEvent({ type: eventType as AgentEvent["type"], ...parsed } as AgentEvent);
          } catch {
            // skip malformed JSON
          }
        }
      }
    }
  }).catch((err) => {
    if (err.name !== "AbortError") {
      onEvent({ type: "error", message: String(err) });
    }
  });

  return { abort: () => controller.abort() };
}
