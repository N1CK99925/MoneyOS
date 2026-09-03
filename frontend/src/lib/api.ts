const API_BASE = '/api'

export async function fetchCatalog() {
  const res = await fetch(`${API_BASE}/catalog`)
  if (!res.ok) throw new Error('Failed to fetch catalog')
  const data = await res.json()
  return data.products ?? data
}

export async function createCheckoutSession(itemId: string, quantity = 1) {
  const res = await fetch(`${API_BASE}/checkout_sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id: itemId, quantity }),
  })
  if (!res.ok) throw new Error('Failed to create checkout session')
  return res.json()
}

export async function getCheckoutSession(id: string) {
  const res = await fetch(`${API_BASE}/checkout_sessions/${id}`)
  if (!res.ok) throw new Error('Failed to fetch session')
  return res.json()
}

export async function completeCheckout(id: string) {
  const res = await fetch(`${API_BASE}/checkout_sessions/${id}/complete?poll=true`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new Error('Failed to complete checkout')
  return res.json()
}

export async function cancelCheckout(id: string) {
  const res = await fetch(`${API_BASE}/checkout_sessions/${id}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new Error('Failed to cancel checkout')
  return res.json()
}

export async function failCheckout(id: string, reason = 'Payment failed') {
  const res = await fetch(`${API_BASE}/checkout_sessions/${id}/fail`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) throw new Error('Failed to mark checkout as failed')
  return res.json()
}

export async function getRazorpayKey() {
  const res = await fetch(`${API_BASE}/razorpay_key`)
  if (!res.ok) throw new Error('Failed to fetch Razorpay key')
  return res.json()
}

export function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]')) {
      resolve(true)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.body.appendChild(script)
  })
}

export async function fetchAuditLog(limit = 50) {
  const res = await fetch(`${API_BASE}/audit?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch audit log')
  return res.json()
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/settings`)
  if (!res.ok) throw new Error('Failed to fetch settings')
  return res.json()
}

export async function updateSetting(key: string, value: string) {
  const res = await fetch(`${API_BASE}/settings/${key}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail || `Failed to update ${key}`)
  }
  return res.json()
}

export function streamAgentRun(
  goal: string,
  onMessage: (data: string, type?: 'message' | 'progress') => void,
  onDone: () => void,
  onError: (err: Error) => void,
  stretch: boolean = false,
  history: { role: string; content: string }[] = [],
) {
  const controller = new AbortController()

  fetch(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, stretch, history }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) throw new Error('Agent request failed')
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response body')
      const decoder = new TextDecoder()
      let buffer = ''
      let finished = false
      let renderedSummary = false

      while (!finished) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''

        for (const chunk of chunks) {
          const lines = chunk.split('\n')
          let eventType = ''
          let data = ''

          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim()
            } else if (line.startsWith('data:')) {
              data = line.slice(5).trim()
            }
          }

          if (!data) continue

          try {
            const parsed = JSON.parse(data)

            if (eventType === 'done' || eventType === 'error') {
              // On a normal completion the 'summary' event already carried the
              // final text — only render here for the error path (no summary).
              const text = parsed.result || parsed.message || ''
              if (text && !renderedSummary) onMessage(text)
              finished = true
              break
            }

            if (eventType === 'summary') {
              renderedSummary = true
              onMessage(parsed.message || '')
            } else if (eventType === 'tool_call') {
              const name = parsed.name || 'unknown'
              const args = parsed.args
              let detail = ''
              if (name === 'search_catalog') detail = `Searching catalog for "${args?.query || '...'}"…`
              else if (name === 'search_and_score') detail = `Researching "${args?.query || '...'}"…`
              else if (name === 'create_checkout_session') detail = 'Creating checkout…'
              else if (name === 'get_payment_link') detail = 'Generating payment page…'
              else if (name === 'pay_with_test_card') detail = 'Preparing test payment…'
              else if (name === 'complete_checkout') detail = 'Verifying payment…'
              else if (name === 'cancel_checkout') detail = 'Canceling order…'
              else if (name === 'get_checkout_session') detail = 'Checking order status…'
              if (detail) onMessage(detail, 'progress')
            } else if (eventType === 'tool_result') {
              const result = parsed.result || ''
              try {
                const json = JSON.parse(result)
                if (json.best_match) {
                  onMessage(`Found: ${json.best_match.name} — ₹${Math.round((json.best_match.price_paise || 0) / 100)}`)
                } else if (json.checkout_url) {
                  // Don't show raw URL as progress — the summary will include it
                } else if (json.card) {
                  // Test card info — will be in summary
                } else if (json.status === 'completed') {
                  onMessage('Payment confirmed', 'progress')
                } else if (json.status === 'pending_approval') {
                  onMessage('Order over budget — pending human approval', 'progress')
                } else if (json.status === 'awaiting_payment') {
                  onMessage('Ready for payment', 'progress')
                }
              } catch {
                // ignore unparseable results
              }
            }
            // Hide: model_switch, model_error, rate_limit_wait (internal details)
          } catch {
            if (data && data !== '{}') onMessage(data + '\n')
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err)
    })

  return () => controller.abort()
}
