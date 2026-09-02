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

  return (
    <div className="min-h-[60dvh] px-4 py-24 md:py-32">
      <div className="max-w-3xl mx-auto">
        {/* ── Header ── */}
        <div ref={headerRef} className="reveal mb-12">
          <span className="inline-flex items-center gap-2 rounded-full bg-parchment px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-ink-muted mb-5">
            <SlidersHorizontal weight="light" className="w-3 h-3" />
            Buy Policy
          </span>
          <h1 className="font-serif text-4xl md:text-5xl font-bold tracking-tight text-ink mb-3">
            Spend Settings
          </h1>
          <p className="text-base text-ink-muted">
            Bounds the buying agent's autonomy. Changes apply instantly to the next checkout — every order is gated by the limit you set here.
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
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.2em] font-medium text-ink-muted">
              Per-transaction spend limit
            </p>
            {settings.map((s, i) => {
              const isPaise = s.key.includes('paise')
              const current = parseInt(s.value, 10) || 0
              const def = parseInt(s.default, 10)
              const isDirty = drafts[s.key] !== undefined && drafts[s.key] !== s.value
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
                      <div className="mt-3 flex items-baseline gap-2">
                        <span className="font-serif text-3xl font-bold text-ink tracking-tight">
                          {isPaise ? formatInr(current) : current}
                        </span>
                        {def > 0 && (
                          <span className="text-xs text-ink-muted">
                            default {isPaise ? formatInr(def) : def}
                          </span>
                        )}
                      </div>
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
                        label={isPaise ? 'Value (paise)' : 'Value'}
                        type="number"
                        min={0}
                        value={drafts[s.key] ?? s.value}
                        onChange={(e) =>
                          setDrafts((p) => ({ ...p, [s.key]: e.target.value }))
                        }
                      />
                      {isPaise && (
                        <p className="text-xs text-ink-muted mt-1.5">
                          Enter 0 to disable the limit entirely.
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
        )}
      </div>
    </div>
  )
}
