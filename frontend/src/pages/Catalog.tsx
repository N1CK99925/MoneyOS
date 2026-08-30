import { useEffect, useState, useMemo } from 'react'
import { ShoppingCart, Plus, Minus, Trash, MagnifyingGlass } from 'phosphor-react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchCatalog, createCheckoutSession, getRazorpayKey, loadRazorpayScript, completeCheckout, cancelCheckout, failCheckout } from '../lib/api'
import type { CatalogItem } from '../types'
import { useGoal } from '../hooks'
import { GlassButton } from '../components/ui/glass-button'

const EASE: [number, number, number, number] = [0.32, 0.72, 0, 1]

export default function Catalog() {
  const [items, setItems] = useState<CatalogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [cart, setCart] = useState<Record<string, number>>({})
  const [search, setSearch] = useState('')
  const [checkoutId, setCheckoutId] = useState<string | null>(null)
  const { addItem } = useGoal()

  useEffect(() => {
    fetchCatalog()
      .then(setItems)
      .catch(() => setError('Failed to load catalog'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!search.trim()) return items
    const q = search.toLowerCase()
    return items.filter(
      (i) =>
        i.name.toLowerCase().includes(q) ||
        (i.description ?? '').toLowerCase().includes(q) ||
        i.id.toLowerCase().includes(q),
    )
  }, [items, search])

  const cartCount = Object.values(cart).reduce((a, b) => a + b, 0)
  const cartTotal = Object.entries(cart).reduce((sum, [id, qty]) => {
    const item = items.find((i) => i.id === id)
    return sum + (item?.price_paise ?? 0) * qty
  }, 0)

  const updateCart = (id: string, delta: number) => {
    setCart((prev) => {
      const next = { ...prev }
      const cur = next[id] ?? 0
      const nextVal = cur + delta
      if (nextVal <= 0) delete next[id]
      else next[id] = nextVal
      return next
    })
  }

  const handleCheckout = async () => {
    const firstItem = Object.entries(cart)[0]
    if (!firstItem) return
    const [itemId, qty] = firstItem
    try {
      const scriptLoaded = await loadRazorpayScript()
      if (!scriptLoaded) {
        setError('Failed to load payment script')
        return
      }
      const [session, keyData] = await Promise.all([
        createCheckoutSession(itemId, qty),
        getRazorpayKey(),
      ])
      setCheckoutId(session.session_id)

      const options = {
        key: keyData.key_id,
        amount: session.total_paise,
        currency: session.currency,
        name: 'MoneyOS',
        description: `Order for ${session.items?.[0]?.name ?? session.session_id}`,
        order_id: session.razorpay_order_id,
        handler: async () => {
          try {
            await completeCheckout(session.session_id)
            setCheckoutId(null)
            setCart({})
          } catch {
            setError('Payment received but confirmation failed. Check audit log.')
          }
        },
        prefill: { name: '', email: '', contact: '' },
        theme: { color: '#17A66B' },
        modal: {
          ondismiss: async () => {
            try { await cancelCheckout(session.session_id) } catch {}
            setCheckoutId(null)
          },
        },
      }

      const rzp = new (window as any).Razorpay(options)
      rzp.on('payment.failed', async (resp: any) => {
        const reason = resp.error?.description ?? 'Payment failed'
        try { await failCheckout(session.session_id, reason) } catch {}
        setError(`Payment failed: ${reason}`)
        setCheckoutId(null)
      })
      rzp.open()
    } catch {
      setError('Checkout failed')
    }
  }

  const handleAgentGoal = (item: CatalogItem) => {
    addItem(item)
  }

  if (loading) {
    return (
      <div className="min-h-[60dvh] flex items-center justify-center px-4">
        <div className="space-y-3 w-full max-w-sm">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-2xl bg-parchment/50 animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[60dvh] px-4 py-24 md:py-32">
      <div className="max-w-5xl mx-auto">
        {/* ── Header ── */}
        <div className="mb-12">
          <span className="inline-flex items-center gap-2 rounded-full bg-parchment px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-ink-muted mb-5">
            <ShoppingCart weight="light" className="w-3 h-3" />
            Marketplace
          </span>
          <h1 className="font-serif text-4xl md:text-5xl font-bold tracking-tight text-ink mb-3">
            Catalog
          </h1>
          <p className="text-base text-ink-muted">
            {items.length} products. Add to cart, or let the agent handle it.
          </p>
        </div>

        {error && (
          <div className="mb-8 rounded-2xl bg-error-surface border border-error-border px-5 py-3 text-sm text-error">
            {error}
          </div>
        )}

        {/* ── Search ── */}
        <div className="relative mb-10">
          <MagnifyingGlass weight="light" className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products..."
            className="w-full rounded-full bg-white border border-border-warm pl-12 pr-5 py-3.5 text-sm text-ink placeholder:text-ink-muted outline-none focus:ring-2 focus:ring-sage/10 focus:border-sage/30 transition-all duration-500 ease-spring"
          />
        </div>

        {/* ── Product grid ── */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          {filtered.map((item, i) => {
            const span =
              i % 5 === 0 ? 'md:col-span-7' :
              i % 5 === 1 ? 'md:col-span-5' :
              i % 5 === 2 ? 'md:col-span-4' :
              i % 5 === 3 ? 'md:col-span-4' :
              'md:col-span-4'
            const qty = cart[item.id] ?? 0

            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: EASE, delay: i * 0.05 }}
                className={span}
              >
                <div className="group h-full rounded-[1.5rem] bg-cream-dark border border-border-faint p-1 transition-all duration-700 ease-spring hover:border-border-warm/60">
                  <div className="h-full rounded-[calc(1.5rem-4px)] bg-white border border-border-faint/50 p-6 inset-highlight flex flex-col justify-between min-h-[220px] transition-all duration-700 ease-spring group-hover:shadow-card-hover">
                    <div>
                      <span className="font-mono text-[10px] text-ink-muted tracking-wider uppercase">{item.id}</span>
                      <h3 className="font-serif text-xl font-semibold text-ink mt-2 mb-2">{item.name}</h3>
                      <p className="text-sm text-ink-muted leading-relaxed line-clamp-3">{item.description ?? ''}</p>
                    </div>
                    <div className="flex items-center justify-between mt-5">
                      <span className="font-mono text-lg font-medium text-ink">
                        ₹{Math.round(item.price_paise / 100)}
                      </span>
                      <div className="flex items-center gap-2">
                        {qty > 0 ? (
                          <div className="flex items-center gap-1 rounded-full bg-parchment border border-border-faint px-1 py-1">
                            <GlassButton
                              size="icon"
                              variant="ghost"
                              onClick={() => updateCart(item.id, -1)}
                              className="!h-7 !w-7 !rounded-full"
                            >
                              {qty === 1 ? (
                                <Trash weight="light" className="w-3 h-3 text-error" />
                              ) : (
                                <Minus weight="light" className="w-3 h-3 text-ink-soft" />
                              )}
                            </GlassButton>
                            <span className="w-6 text-center font-mono text-xs font-medium text-ink">{qty}</span>
                            <GlassButton
                              size="icon"
                              variant="ghost"
                              onClick={() => updateCart(item.id, 1)}
                              className="!h-7 !w-7 !rounded-full"
                            >
                              <Plus weight="light" className="w-3 h-3 text-ink-soft" />
                            </GlassButton>
                          </div>
                        ) : (
                          <GlassButton
                            size="icon"
                            variant="ghost"
                            onClick={() => updateCart(item.id, 1)}
                            className="!h-9 !w-9 !rounded-full"
                          >
                            <Plus weight="light" className="w-4 h-4" />
                          </GlassButton>
                        )}
                        <GlassButton
                          size="icon"
                          onClick={() => handleAgentGoal(item)}
                          className="!h-9 !w-9 !rounded-full"
                          title="Ask agent to buy this"
                        >
                          <ShoppingCart weight="light" className="w-4 h-4" />
                        </GlassButton>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* ── Cart bar ── */}
        <AnimatePresence>
          {cartCount > 0 && (
            <motion.div
              initial={{ y: 100, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 100, opacity: 0 }}
              transition={{ duration: 0.6, ease: EASE }}
              className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-[calc(100%-2rem)] max-w-lg"
            >
              <div className="rounded-full bg-ink/90 backdrop-blur-xl border border-white/10 px-6 py-4 flex items-center justify-between shadow-dropdown">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                    <ShoppingCart weight="light" className="w-4 h-4 text-cream" />
                  </div>
                  <div>
                    <span className="text-cream text-sm font-medium">{cartCount} items</span>
                    <span className="text-cream/50 text-xs ml-2 font-mono">
                      ₹{Math.round(cartTotal / 100)}
                    </span>
                  </div>
                </div>
                <GlassButton
                  size="sm"
                  variant="sage"
                  onClick={handleCheckout}
                >
                  Checkout
                </GlassButton>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Checkout session display ── */}
        {checkoutId && (
          <div className="mt-8 rounded-2xl bg-sage-pale border border-sage/10 px-6 py-4 text-sm text-ink flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-sage animate-pulse" />
            <span className="font-medium">Waiting for payment...</span>
            <span className="text-ink-muted font-mono text-xs ml-auto">{checkoutId}</span>
          </div>
        )}
      </div>
    </div>
  )
}
