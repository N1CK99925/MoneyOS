import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { SlidersHorizontal, Check, ArrowCounterClockwise } from 'phosphor-react'
import { fetchSettings, updateSetting } from '../lib/api'
import type { SystemSetting } from '../types'
import { useScrollReveal } from '../hooks'
import { GlassButton } from '../components/ui/glass-button'
import Input from '../components/ui/Input'

const EASE: [number, number, number, number] = [0.32, 0.72, 0, 1]

const prettyLabel = (key: string) =>
  key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())

const formatInr = (paise: number) => `₹${(paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

const isNumeric = (s: SystemSetting) =>
  s.key.includes('paise') || /^\d+$/.test(s.value)

const isSensitive = (key: string) => key === 'telegram_bot_token'

type SettingGroup = {
  label: string
  description: string
  settings: SystemSetting[]
}

const groupSettings = (settings: SystemSetting[]): SettingGroup[] => {
  const groups: SettingGroup[] = [
    { label: 'Spend Policy', description: 'Bounds the buying agent\'s autonomy.', settings: [] },
    { label: 'Telegram Delivery', description: 'Bot token and chat IDs for payment & approval delivery.', settings: [] },
  ]

  for (const s of settings) {
    if (s.key.startsWith('telegram_')) {
      groups[1].settings.push(s)
    } else {
      groups[0].settings.push(s)
    }
  }

  return groups.filter((g) => g.settings.length > 0)
}

export default function Settings() {
  const [settings, setSettings] = useState<SystemSetting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saved, setSaved] = useState<Record<string, string>>({})
  const headerRef = useScrollReveal()

  useEffect(() => {
    fetchSettings()
      .then((data: SystemSetting[]) => {
        const list = Array.isArray(data) ? data : []
        setSettings(list)
        const init: Record<string, string> = {}
        list.forEach((s) => (init[s.key] = s.value))
        setDrafts(init)
      })
      .catch(() => setError('Failed to load settings'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async (key: string) => {
    const value = drafts[key]
    if (value === undefined) return
    setSaving((p) => ({ ...p, [key]: true }))
    setSaved((p) => ({ ...p, [key]: '' }))
    try {
      await updateSetting(key, value)
      setSaved((p) => ({ ...p, [key]: 'Saved' }))
      setSettings((prev) =>
        prev.map((s) => (s.key === key ? { ...s, value } : s)),
      )
      setTimeout(() => {
        setSaved((p) => {
          const next = { ...p }
          delete next[key]
          return next
        })
      }, 2000)
    } catch (e) {
      setSaved((p) => ({ ...p, [key]: e instanceof Error ? e.message : 'Error' }))
    } finally {
      setSaving((p) => ({ ...p, [key]: false }))
    }
  }

  const handleReset = (key: string, def: string) => {
    setDrafts((p) => ({ ...p, [key]: def }))
  }

  const groups = groupSettings(settings)

  return (
    <div className="min-h-[60dvh] px-4 py-24 md:py-32">
      <div className="max-w-3xl mx-auto">
        {/* ── Header ── */}
        <div ref={headerRef} className="reveal mb-12">
          <span className="inline-flex items-center gap-2 rounded-full bg-parchment px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-ink-muted mb-5">
            <SlidersHorizontal weight="light" className="w-3 h-3" />
            System Settings
          </span>
          <h1 className="font-serif text-4xl md:text-5xl font-bold tracking-tight text-ink mb-3">
            Settings
          </h1>
          <p className="text-base text-ink-muted">
            Configure spend policy and delivery. Changes apply instantly — no restart needed.
          </p>
        </div>

        {error && (
          <div className="mb-8 rounded-2xl bg-error-surface border border-error-border px-5 py-3 text-sm text-error">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-28 rounded-2xl bg-parchment/50 animate-pulse" />
            ))}
          </div>
        ) : settings.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-14 h-14 rounded-full bg-parchment border border-border-faint flex items-center justify-center mx-auto mb-5">
              <SlidersHorizontal weight="light" className="w-6 h-6 text-ink-muted" />
            </div>
            <p className="text-sm text-ink-muted">No editable settings yet.</p>
          </div>
        ) : (
          <div className="space-y-12">
            {groups.map((group) => (
              <div key={group.label}>
                <p className="text-xs uppercase tracking-[0.2em] font-medium text-ink-muted mb-4">
                  {group.label}
                </p>
                <div className="space-y-4">
                  {group.settings.map((s, i) => {
                    const numeric = isNumeric(s)
                    const sensitive = isSensitive(s.key)
                    const currentVal = drafts[s.key] ?? s.value
                    const isDirty = currentVal !== s.value
                    return (
                      <motion.div
                        key={s.key}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, ease: EASE, delay: i * 0.05 }}
                        className="rounded-[1.25rem] bg-cream-dark border border-border-faint p-5 md:p-6"
                      >
                        <div className="flex items-start justify-between gap-6">
                          <div className="min-w-0">
                            <h3 className="font-display text-lg font-semibold text-ink tracking-tight">
                              {prettyLabel(s.key)}
                            </h3>
                            {s.description && (
                              <p className="text-sm text-ink-muted mt-1">{s.description}</p>
                            )}
                            {numeric ? (
                              <div className="mt-3 flex items-baseline gap-2">
                                <span className="font-serif text-3xl font-bold text-ink tracking-tight">
                                  {s.key.includes('paise') ? formatInr(parseInt(s.value, 10) || 0) : s.value}
                                </span>
                                {parseInt(s.default, 10) > 0 && (
                                  <span className="text-xs text-ink-muted">
                                    default {s.key.includes('paise') ? formatInr(parseInt(s.default, 10)) : s.default}
                                  </span>
                                )}
                              </div>
                            ) : (
                              <div className="mt-3">
                                <span className={`text-sm font-mono ${currentVal ? 'text-ink' : 'text-ink-muted italic'}`}>
                                  {currentVal || 'Not configured'}
                                </span>
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {saved[s.key] && (
                              <span className={`text-xs font-medium ${saved[s.key] === 'Saved' ? 'text-sage' : 'text-error'}`}>
                                {saved[s.key]}
                              </span>
                            )}
                            <GlassButton
                              size="icon"
                              variant="ghost"
                              onClick={() => handleReset(s.key, s.default)}
                              aria-label="Reset to default"
                              className="!h-9 !w-9"
                            >
                              <ArrowCounterClockwise weight="light" className="w-4 h-4" />
                            </GlassButton>
                          </div>
                        </div>

                        <div className="mt-4 flex items-end gap-3">
                          <div className="flex-1">
                            <Input
                              label={numeric ? (s.key.includes('paise') ? 'Value (paise)' : 'Value') : s.key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                              type={sensitive ? 'password' : numeric ? 'number' : 'text'}
                              {...(numeric ? { min: 0 } : {})}
                              value={currentVal}
                              onChange={(e) =>
                                setDrafts((p) => ({ ...p, [s.key]: e.target.value }))
                              }
                            />
                            {s.key.includes('paise') && (
                              <p className="text-xs text-ink-muted mt-1.5">
                                Enter 0 to disable the limit entirely.
                              </p>
                            )}
                            {sensitive && (
                              <p className="text-xs text-ink-muted mt-1.5">
                                Get from @BotFather on Telegram.
                              </p>
                            )}
                          </div>
                          <GlassButton
                            size="sm"
                            variant={isDirty ? 'sage' : 'ghost'}
                            disabled={!isDirty || saving[s.key]}
                            onClick={() => handleSave(s.key)}
                            contentClassName="flex items-center gap-2 !px-5"
                          >
                            {saving[s.key] ? (
                              <span className="w-3.5 h-3.5 rounded-full border-2 border-cream/40 border-t-cream animate-spin" />
                            ) : (
                              <Check weight="bold" className="w-4 h-4" />
                            )}
                            <span>{saving[s.key] ? 'Saving…' : 'Apply'}</span>
                          </GlassButton>
                        </div>
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── How Telegram Delivery Works ── */}
        <div className="mt-16 rounded-[1.25rem] bg-cream-dark border border-border-faint p-6 md:p-8">
          <h2 className="font-display text-lg font-semibold text-ink tracking-tight mb-2">
            How Telegram Delivery Works
          </h2>
          <p className="text-sm text-ink-muted mb-6">
            The bot sends payment links and Approve/Deny cards to a Telegram chat. Here's how to set it up and its current limits.
          </p>

          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-ink mb-3">Getting your values</h3>
              <ol className="space-y-2 text-sm text-ink-muted list-decimal list-inside">
                <li>
                  <span className="text-ink">Bot Token</span> — chat <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">@BotFather</code> on Telegram and use <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">/newbot</code> to create one. Copy the token string (e.g. <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">123456:ABC-DEF...)</code>.
                </li>
                <li>
                  <span className="text-ink">Chat IDs</span> — open your bot and tap <span className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">Start</span>, then send any message. Fetch it from your browser: visit <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">https://api.telegram.org/bot&#123;TOKEN&#125;/getUpdates</code> and copy the number under <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">"chat":&#123;"id":…&#125;</code>.
                </li>
                <li>
                  <span className="text-ink">Customer Chat ID</span> — for a demo where you're both ends, use the same number as the merchant. Otherwise leave it blank to fall back to the merchant chat.
                </li>
              </ol>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-ink mb-3">Current limits</h3>
              <ul className="space-y-2 text-sm text-ink-muted list-disc list-inside">
                <li>
                  <span className="text-ink">Bot token and chat IDs are set manually.</span> There's no self-serve sign-up — a real customer can't configure themselves yet. Setting these here is only for the merchant's demo.
                </li>
                <li>
                  <span className="text-ink">Telegram bots can only message users who've started them.</span> So a customer must open the bot and press <span className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">Start</span> before the bot can send them a payment link.
                </li>
                <li>
                  <span className="text-ink">No automatic chat-ID capture yet.</span> Right now the chat ID has to be copied out of <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">getUpdates</code> JSON by hand. A future <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">/start</code> handler would capture it automatically (e.g. via a <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">?start=&#123;session&#125;</code> deep link) so a normal user doesn't need to configure anything.
                </li>
                <li>
                  <span className="text-ink">Keep your bot token private.</span> Don't share it or commit it to version control — anyone with the token can control the bot. Regenerate it via <code className="font-mono text-xs bg-parchment px-1.5 py-0.5 rounded">/revoke</code> if it leaks.
                </li>
              </ul>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-ink mb-3">How the flow plays out</h3>
              <ol className="space-y-2 text-sm text-ink-muted list-decimal list-inside">
                <li>A buyer agent creates a checkout and completes it.</li>
                <li>The system pushes the payment link to the customer's Telegram chat.</li>
                <li>Once paid, an Approve/Deny card is sent to the merchant's Telegram chat.</li>
                <li>Tapping a button approves or denies the purchase — and the card shows the result.</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
