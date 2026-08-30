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

export async function getRazorpayKey() {
  const res = await fetch(`${API_BASE}/razorpay_key`)
  if (!res.ok) throw new Error('Failed to fetch Razorpay key')
  return res.json()
}

export async function fetchAuditLog(limit = 50) {
  const res = await fetch(`${API_BASE}/audit?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch audit log')
  return res.json()
}

export function streamAgentRun(
  goal: string,
  onMessage: (data: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  stretch: boolean = false,
) {
  const controller = new AbortController()

  fetch(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, stretch }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) throw new Error('Agent request failed')
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response body')
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
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
              const text = parsed.result || parsed.message || ''
              if (text) onMessage(text)
              onDone()
              return
            }

            if (eventType === 'summary') {
              onMessage(parsed.message || '')
            } else if (eventType === 'tool_call') {
              const name = parsed.name || 'unknown'
              const args = parsed.args
              let detail = `[calling ${name}]`
              if (name === 'search_catalog') detail = `[searching catalog: ${args?.query || ''}]`
              else if (name === 'search_and_score') detail = `[researching: ${args?.query || ''}]`
              else if (name === 'create_checkout_session') detail = `[creating checkout]`
              else if (name === 'complete_checkout') detail = `[completing payment]`
              else if (name === 'cancel_checkout') detail = `[canceling order]`
              else if (name === 'get_checkout_session') detail = `[checking status]`
              onMessage(`\n${detail}\n`)
            } else if (eventType === 'tool_result') {
              const result = parsed.result || ''
              try {
                const json = JSON.parse(result)
                if (json.best_match) {
                  onMessage(`Found: ${json.best_match.name} — rating ${json.best_match.rating || 'N/A'}, ${json.best_match.review_count || 0} reviews, ₹${Math.round((json.best_match.price_paise || 0) / 100)}\n`)
                } else if (json.matches) {
                  onMessage(`Found ${json.matches.length} items\n`)
                } else if (json.status === 'completed') {
                  onMessage(`Payment confirmed\n`)
                } else if (json.message) {
                  onMessage(`${json.message}\n`)
                }
              } catch {
                if (result.length > 100) onMessage(`${result.slice(0, 100)}...\n`)
              }
            } else if (eventType === 'model_switch') {
              onMessage(`[using ${parsed.model}]\n`)
            } else if (eventType === 'model_error') {
              onMessage(`[${parsed.model} failed, trying next]\n`)
            } else if (eventType === 'rate_limit_wait') {
              onMessage(`[rate limited — waiting ${parsed.seconds}s]\n`)
            }
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
